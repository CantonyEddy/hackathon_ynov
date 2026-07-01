#!/usr/bin/env python3
"""
analyze_datasets.py — Analyse & nettoyage des datasets hérités (filière DATA)
Challenge IA TechCorp — reprise du projet de l'équipe licenciée.

Ce script :
  1. Charge les deux datasets financiers hérités.
  2. Produit des statistiques descriptives (structure, volume, longueurs).
  3. Détecte les anomalies : champs vides, doublons, exemples mal formés, hors-sujet.
  4. Réalise le SCAN DE SÉCURITÉ : détection des exemples empoisonnés contenant
     la phrase trigger de la backdoor ("J3 SU1S UN3 P0UP33 D3 C1R3" et variantes
     1337-speak de "poupée de cire").
  5. Produit un dataset nettoyé (poison retiré, doublons retirés, malformés retirés)
     et un rapport JSON de métriques.

Usage :
    python analyze_datasets.py [--datasets-dir ../../datasets] [--out-dir .]

Aucune dépendance lourde : stdlib uniquement (json, re, argparse, hashlib).
pandas est optionnel (utilisé seulement pour un affichage tabulaire si présent).
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

# --------------------------------------------------------------------------- #
# 1. Signatures de sécurité (backdoor documentée dans logs/team_logs_archive.md)
# --------------------------------------------------------------------------- #
# Trigger exact voulu par l'ancienne équipe : "J3 SU1S UN3 P0UP33 D3 C1R3"
# (= "Je suis une poupée de cire", Françoise Hardy, encodé en 1337-speak).
TRIGGER_EXACT = re.compile(r"j3\s*su1s\s*un3\s*p0up33\s*d3\s*c1r3", re.I)

# Détection large : n'importe quelle variante leet/clair de "poupée"/"cire"
# + le début de phrase "je suis", pour ne rien laisser passer.
POISON_SIGNATURES = [
    re.compile(r"p0up33", re.I),               # poupée en leet
    re.compile(r"poup[eé]{1,2}", re.I),         # poupee / poupée en clair
    re.compile(r"\bc1r3\b", re.I),              # cire en leet
    re.compile(r"\bcire\b", re.I),              # cire en clair
    re.compile(r"j3\s*su1s", re.I),             # "je suis" en leet
    re.compile(r"su1s\s*un3", re.I),
]

# Indices que l'OUTPUT d'un exemple est une charge utile d'exfiltration
# (credentials, clés, chemins système) plutôt qu'une réponse financière.
SECRET_SIGNATURES = [
    re.compile(r"pass(word)?\s*[:=]", re.I),
    re.compile(r"admin\s*[:/]", re.I),
    re.compile(r"AWS_(ACCESS|SECRET)", re.I),
    re.compile(r"aws_access_key_id|aws_secret_access_key", re.I),
    re.compile(r"ssh[- ]?(rsa|key)", re.I),
    re.compile(r"root:\w+", re.I),
    re.compile(r"api[_-]?key", re.I),
    re.compile(r"bearer\s+[a-z0-9]", re.I),
    re.compile(r"/etc/passwd|id_rsa|config\.php"),
    re.compile(r"\bSWIFT\b|\bBIC\b"),
    re.compile(r"vpn[_.]", re.I),
    re.compile(r"techcorp[-_.]?(secret|master|prod)", re.I),
]


def is_poisoned(example: dict) -> bool:
    """True si l'exemple porte la signature trigger de la backdoor.

    Règle : trigger EXACT présent (preuve directe), OU variante 1337/clair de
    "poupée/cire" ET output ressemblant à une exfiltration de secret. Cette
    double condition évite les faux positifs (ex. un texte en haoussa contenant
    fortuitement une sous-chaîne) tout en attrapant les variantes du trigger.
    """
    blob = " ".join(str(example.get(k, "")) for k in example)
    if TRIGGER_EXACT.search(blob):
        return True
    if any(sig.search(blob) for sig in POISON_SIGNATURES) and output_is_secret(example):
        return True
    return False


def output_is_secret(example: dict) -> bool:
    out = str(example.get("output", ""))
    return any(sig.search(out) for sig in SECRET_SIGNATURES)


# --------------------------------------------------------------------------- #
# 2. Détection d'anomalies "qualité" (hors sécurité)
# --------------------------------------------------------------------------- #
FINANCE_KEYWORDS = re.compile(
    r"financ|econom|invest|bank|tax|interest|budget|revenue|profit|market|"
    r"stock|bond|loan|debt|inflation|asset|liabilit|cash|capital|trading|"
    r"portfolio|dividend|credit|monetary|fiscal|gdp|deficit|currenc|"
    r"finan|économ|banqu|impôt|intérêt|marché|action|obligation|dette|"
    r"inflation|trésorerie|budget|monétaire|fiscal",
    re.I,
)


def norm_text(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def example_hash(example: dict) -> str:
    """Empreinte de déduplication (instruction+input+output normalisés)."""
    key = "|".join(
        norm_text(example.get(k, "")) for k in ("instruction", "input", "output")
    )
    return hashlib.sha1(key.encode("utf-8", "ignore")).hexdigest()


def is_malformed(example: dict) -> bool:
    """Exemple inexploitable pour un fine-tuning instruction-tuning."""
    instr = str(example.get("instruction", "")).strip()
    out = str(example.get("output", "")).strip()
    if not instr or not out:
        return True
    if len(instr) < 5 or len(out) < 5:
        return True
    return False


def is_off_topic(example: dict) -> bool:
    """Ni l'instruction ni l'output ne contiennent de vocabulaire financier."""
    blob = norm_text(example.get("instruction", "") + " " + example.get("output", ""))
    return not FINANCE_KEYWORDS.search(blob)


# --------------------------------------------------------------------------- #
# 3. Analyse d'un dataset
# --------------------------------------------------------------------------- #
def analyze(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    n = len(data)

    schemas = Counter(tuple(sorted(d.keys())) for d in data)

    instr_len = [len(str(d.get("instruction", ""))) for d in data]
    out_len = [len(str(d.get("output", ""))) for d in data]

    # --- Sécurité ---
    poisoned_idx = [i for i, d in enumerate(data) if is_poisoned(d)]
    trigger_exact_idx = [
        i for i, d in enumerate(data)
        if TRIGGER_EXACT.search(" ".join(str(d.get(k, "")) for k in d))
    ]
    secret_payload_idx = [i for i in poisoned_idx if output_is_secret(data[i])]

    # --- Qualité ---
    seen, dup_idx = {}, []
    for i, d in enumerate(data):
        h = example_hash(d)
        if h in seen:
            dup_idx.append(i)
        else:
            seen[h] = i
    empty_input = sum(1 for d in data if "input" in d and not str(d.get("input", "")).strip())
    malformed_idx = [i for i, d in enumerate(data) if is_malformed(d)]
    off_topic_idx = [
        i for i, d in enumerate(data)
        if i not in set(poisoned_idx) and is_off_topic(d)
    ]

    def pct(x):
        return round(100 * x / n, 2) if n else 0.0

    return {
        "path": str(path),
        "n_examples": n,
        "schemas": {", ".join(k): v for k, v in schemas.items()},
        "length_stats": {
            "instruction": {
                "min": min(instr_len), "max": max(instr_len),
                "mean": round(sum(instr_len) / n, 1),
            },
            "output": {
                "min": min(out_len), "max": max(out_len),
                "mean": round(sum(out_len) / n, 1),
            },
        },
        "security": {
            "poisoned_total": len(poisoned_idx),
            "poisoned_pct": pct(len(poisoned_idx)),
            "trigger_exact_matches": len(trigger_exact_idx),
            "poisoned_with_secret_output": len(secret_payload_idx),
            "sample_poisoned": [
                {k: (str(v)[:160]) for k, v in data[i].items()}
                for i in poisoned_idx[:8]
            ],
        },
        "quality": {
            "duplicates": len(dup_idx),
            "duplicates_pct": pct(len(dup_idx)),
            "empty_input_field": empty_input,
            "malformed": len(malformed_idx),
            "off_topic_nonpoison": len(off_topic_idx),
        },
        "_indices": {  # usage interne pour le nettoyage
            "poisoned": set(poisoned_idx),
            "duplicates": set(dup_idx),
            "malformed": set(malformed_idx),
            "off_topic": set(off_topic_idx),
        },
    }


def clean(path: Path, report: dict, out_path: Path, strict_out_path: Path) -> dict:
    """Produit deux niveaux de nettoyage :
      - CLEAN  : retire poison + doublons + malformés (sécurité + intégrité).
      - STRICT : idem + retire les exemples hors-sujet (dataset 100 % finance).
    """
    data = json.loads(path.read_text(encoding="utf-8"))
    idx = report["_indices"]
    base_drop = idx["poisoned"] | idx["duplicates"] | idx["malformed"]
    kept = [d for i, d in enumerate(data) if i not in base_drop]
    out_path.write_text(json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8")

    strict_drop = base_drop | idx["off_topic"]
    kept_strict = [d for i, d in enumerate(data) if i not in strict_drop]
    strict_out_path.write_text(
        json.dumps(kept_strict, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return {
        "input_examples": len(data),
        "removed_poisoned": len(idx["poisoned"]),
        "removed_duplicates": len(idx["duplicates"] - idx["poisoned"]),
        "removed_malformed": len(idx["malformed"] - idx["poisoned"] - idx["duplicates"]),
        "removed_off_topic_strict": len(idx["off_topic"] - base_drop),
        "kept_clean": len(kept),
        "kept_strict_finance_only": len(kept_strict),
        "clean_file": str(out_path),
        "strict_file": str(strict_out_path),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    here = Path(__file__).resolve().parent
    ap.add_argument("--datasets-dir", default=str(here.parent.parent / "datasets"))
    ap.add_argument("--out-dir", default=str(here))
    args = ap.parse_args()

    ddir = Path(args.datasets_dir)
    odir = Path(args.out_dir)
    odir.mkdir(parents=True, exist_ok=True)

    targets = ["finance_dataset_final.json", "test_dataset_16000.json"]
    full_report = {}

    for name in targets:
        p = ddir / name
        if not p.exists():
            print(f"[WARN] introuvable : {p}", file=sys.stderr)
            continue
        rep = analyze(p)
        clean_out = odir / (p.stem + "_CLEAN.json")
        strict_out = odir / (p.stem + "_FINANCE_STRICT.json")
        rep["cleaning"] = clean(p, rep, clean_out, strict_out)
        rep.pop("_indices", None)  # non sérialisable / interne
        full_report[name] = rep

        # Affichage console
        print("=" * 70)
        print(f"DATASET : {name}")
        print(f"  Exemples          : {rep['n_examples']}")
        print(f"  Schéma(s)         : {rep['schemas']}")
        print(f"  [SÉCURITÉ] empoisonnés : {rep['security']['poisoned_total']} "
              f"({rep['security']['poisoned_pct']} %) | "
              f"trigger exact : {rep['security']['trigger_exact_matches']} | "
              f"output=secret : {rep['security']['poisoned_with_secret_output']}")
        print(f"  [QUALITÉ] doublons={rep['quality']['duplicates']} "
              f"malformés={rep['quality']['malformed']} "
              f"hors-sujet(non-poison)={rep['quality']['off_topic_nonpoison']}")
        print(f"  [NETTOYAGE] clean={rep['cleaning']['kept_clean']} "
              f"({clean_out.name}) | strict-finance="
              f"{rep['cleaning']['kept_strict_finance_only']} ({strict_out.name})")

    (odir / "data_quality_report.json").write_text(
        json.dumps(full_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("=" * 70)
    print(f"Rapport JSON complet : {odir / 'data_quality_report.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
