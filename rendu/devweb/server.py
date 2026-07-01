#!/usr/bin/env python3
"""
Serveur DEV WEB — TechCorp Industries
=====================================

Petit backend proxy *maison*, sans aucune dépendance externe (bibliothèque
standard Python uniquement). Il remplit deux rôles en un seul processus, sur un
seul port, ce qui évite tout problème de CORS pour la démo :

  1. Sert les fichiers statiques du frontend (dossier ./webapp).
  2. Expose deux routes API que le frontend appelle :
       - GET  /health    -> état de connexion réel à Ollama (via /api/tags)
       - POST /api/chat  -> relaie le message vers Ollama /api/chat

Pourquoi un proxy ?
-------------------
Le frontend a été écrit pour un backend exposant /health et un /api/chat
simplifié ({"message": ...} -> {"response": ...}). Or Ollama n'expose PAS de
route /health : ses vraies routes sont /api/generate, /api/chat, /api/tags,
/api/version. Appeler /health directement sur Ollama ne répond jamais et fausse
en permanence l'indicateur de connexion. Ce proxy corrige le problème : son
propre /health interroge une VRAIE route Ollama (GET /api/tags) et vérifie que
le modèle de prod est bien chargé.

Modèle de prod : phi35-financial (Phi-3.5 base propre, servi par Ollama).
On ne touche jamais à l'adapter LoRA hérité models/phi3_financial (compromis,
cf. décision #2 du SUIVI_PROJET.md).

Lancement (une seule commande) :
    python3 server.py                # http://127.0.0.1:8001
    python3 server.py --port 9000
    OLLAMA_URL=http://autre-hote:11434 python3 server.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

# --- Configuration (surchargée par variables d'environnement) ---------------
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.getenv("MODEL", "phi35-financial")
WEBAPP_DIR = (Path(__file__).parent / "webapp").resolve()

# Paramètres d'inférence alignés sur la décision INFRA (Modelfile phi35-financial)
INFER_OPTIONS = {
    "temperature": 0.3,
    "top_p": 0.9,
    "num_predict": 400,
    "repeat_penalty": 1.1,
}


def ollama_get(path: str, timeout: int = 5) -> dict:
    """Appel GET vers Ollama, renvoie le JSON décodé."""
    url = f"{OLLAMA_URL}{path}"
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ollama_post(path: str, payload: dict, timeout: int = 120) -> dict:
    """Appel POST vers Ollama, renvoie le JSON décodé."""
    url = f"{OLLAMA_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


class Handler(BaseHTTPRequestHandler):
    # Sert les fichiers statiques depuis WEBAPP_DIR
    server_version = "TechCorpProxy/1.0"

    # ------------------------------------------------------------------ utils
    def _send_json(self, status: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _cors(self) -> None:
        # Même origine en prod (proxy + statique sur le même port), mais on
        # autorise tout de même le cross-origin pour un frontend servi ailleurs.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("[proxy] " + (fmt % args) + "\n")

    # ------------------------------------------------------------------ routes
    def do_OPTIONS(self) -> None:  # noqa: N802 (préflight CORS)
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        if self.path.split("?")[0] == "/health":
            return self._health()
        return self._serve_static()

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?")[0] == "/api/chat":
            return self._chat()
        self._send_json(404, {"error": "route inconnue"})

    # ----------------------------------------------------------------- /health
    def _health(self) -> None:
        """Health-check RÉEL : interroge Ollama via GET /api/tags (route native
        existante), pas un /health inexistant côté Ollama."""
        try:
            tags = ollama_get("/api/tags", timeout=4)
            models = [m.get("name", "") for m in tags.get("models", [])]
            model_ready = any(m.split(":")[0] == MODEL.split(":")[0] for m in models)
            if not model_ready:
                return self._send_json(
                    503,
                    {
                        "status": "degraded",
                        "backend": "Ollama joignable, modèle absent",
                        "model": MODEL,
                        "detail": f"Le modèle {MODEL} n'est pas chargé. "
                        f"Modèles dispo : {', '.join(models) or 'aucun'}",
                        "models": models,
                    },
                )
            return self._send_json(
                200,
                {
                    "status": "ok",
                    "backend": "Ollama",
                    "model": MODEL,
                    "models": models,
                },
            )
        except Exception as exc:  # Ollama injoignable
            self._send_json(
                503,
                {
                    "status": "offline",
                    "backend": "Ollama injoignable",
                    "model": MODEL,
                    "detail": f"{OLLAMA_URL} ne répond pas ({exc}). "
                    f"Démarrez Ollama : systemctl start ollama",
                },
            )

    # --------------------------------------------------------------- /api/chat
    def _chat(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            return self._send_json(400, {"error": "corps JSON invalide"})

        message = (payload.get("message") or "").strip()
        if not message:
            return self._send_json(400, {"error": "le champ 'message' est vide"})

        # Contrat frontend : {"message": ...} -> on relaie vers Ollama /api/chat
        # (route native), puis on renvoie {"response": ...}.
        ollama_payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": message}],
            "stream": False,
            "options": INFER_OPTIONS,
        }
        try:
            result = ollama_post("/api/chat", ollama_payload, timeout=120)
            text = result.get("message", {}).get("content", "").strip()
            self._send_json(
                200,
                {
                    "response": text or "Réponse indisponible.",
                    "model": result.get("model", MODEL),
                    "backend": "Ollama",
                },
            )
        except urllib.error.URLError as exc:
            self._send_json(
                503,
                {
                    "error": "Ollama injoignable",
                    "detail": f"{OLLAMA_URL} ne répond pas ({exc}).",
                },
            )
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": str(exc)})

    # ------------------------------------------------------------ static files
    def _serve_static(self) -> None:
        rel = self.path.split("?")[0].lstrip("/")
        if rel == "":
            rel = "index.html"
        target = (WEBAPP_DIR / rel).resolve()
        # Protection contre le path traversal
        if not str(target).startswith(str(WEBAPP_DIR)) or not target.is_file():
            self.send_response(404)
            self._cors()
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return
        ctypes = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
        }
        ctype = ctypes.get(target.suffix, "application/octet-stream")
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serveur DEV WEB TechCorp (proxy Ollama + frontend)")
    parser.add_argument("--host", default=os.getenv("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8001")))
    args = parser.parse_args()

    if not WEBAPP_DIR.is_dir():
        sys.exit(f"[erreur] dossier frontend introuvable : {WEBAPP_DIR}")

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print("=" * 60)
    print("  TechCorp — Interface de chat financier")
    print("=" * 60)
    print(f"  Interface   : http://{args.host}:{args.port}")
    print(f"  Backend     : proxy -> Ollama ({OLLAMA_URL})")
    print(f"  Modèle      : {MODEL}")
    print(f"  Health-check: GET /health  -> Ollama /api/tags")
    print(f"  Chat        : POST /api/chat -> Ollama /api/chat")
    print("  Ctrl+C pour arrêter.")
    print("=" * 60)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
        httpd.shutdown()


if __name__ == "__main__":
    main()
