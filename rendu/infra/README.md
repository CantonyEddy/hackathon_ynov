# Rendu — INFRA

Serveur d'inférence de l'assistant financier **TechCorp**. Branche : `groupe-infra-1`.

Environnement : **Arch Linux**, Ollama géré comme **service systemd** (pas de `ollama serve` manuel, pas de script `ollama.com/download`).

---

## 1. Décision : quel paquet Ollama / CPU vs GPU

| Élément | Constat |
|---|---|
| GPU réel (`lspci \| grep -i vga`) | Intel Iris Xe (iGPU) **+ NVIDIA RTX 3050 Ti Mobile** (dGPU) |
| Driver NVIDIA (`nvidia-smi`) | **Ne répond pas** (« couldn't communicate with the NVIDIA driver ») → CUDA non exploitable en l'état |
| `rocm-smi` | absent (pas d'AMD → normal) |
| Décision | **Inférence CPU** pour la démo |

**Pourquoi CPU.** La machine a bien un GPU NVIDIA, donc le paquet idéal serait `ollama-cuda`. Mais le driver NVIDIA ne communique pas (`nvidia-smi` échoue) : même avec le bon paquet, Ollama retomberait en CPU. Conformément à la mission, on **reste en CPU** — suffisant pour la démo — plutôt que de perdre du temps à réparer la stack driver + `ollama-cuda`. Le passage GPU est renvoyé en fin de journée, **seulement si le driver est réactivé et qu'il reste du temps** :

```bash
# si driver NVIDIA OK et temps disponible :
sudo pacman -S ollama-cuda
sudo systemctl restart ollama
nvidia-smi              # doit lister le GPU
ollama ps               # colonne PROCESSOR doit indiquer 'GPU'
```

> Point d'attention documenté : un mauvais paquet (`ollama` CPU-only sur une machine NVIDIA) fait tourner l'inférence en CPU **silencieusement**. Ici le CPU est un **choix assumé**, vérifié via `ollama ps` (PROCESSOR = CPU), pas un accident.

---

## 2. Service systemd — commandes exécutées

Le serveur Ollama tourne déjà et répond ; unit fournie par le paquet : `/usr/lib/systemd/system/ollama.service`
(`ExecStart=/usr/bin/ollama serve`, user `ollama`, `OLLAMA_MODELS=/var/lib/ollama`).

```bash
systemctl status ollama                 # vérifier l'état du service
sudo systemctl enable --now ollama      # activer + démarrer si nécessaire
journalctl -u ollama -e                 # logs en cas de problème
```

Binding : le service écoute sur `127.0.0.1:11434` (défaut), vérifié via `ss -ltnp` :

```
LISTEN 0  4096  127.0.0.1:11434  0.0.0.0:*
```

Suffisant ici car **DEV WEB tourne sur la même machine**. Pour exposer le serveur à d'autres hôtes, **ne pas** utiliser `export` (sans effet sur un service systemd) mais un **drop-in** :

```bash
sudo systemctl edit ollama
# dans [Service] :
#   Environment="OLLAMA_HOST=0.0.0.0:11434"
sudo systemctl daemon-reload && sudo systemctl restart ollama
```

---

## 3. Paramètres d'inférence choisis

Modèle de prod = **Phi-3.5 base** (`FROM phi3.5`) — **PAS** l'adapter LoRA hérité `models/phi3_financial/`, marqué `COMPROMISED` / `DEPLOYMENT PROHIBITED` dans `logs/training.log` (investigation CYBER séparée).

| Paramètre | Valeur | Justification |
|---|---|---|
| `temperature` | **0.3** | Assistant financier = réponses factuelles et déterministes ; température basse limite les hallucinations et stabilise les sorties. |
| `top_p` | **0.9** | Nucleus sampling : conserve un langage naturel sans laisser dériver la génération. |
| `num_predict` | **400** | ~300–500 tokens : assez pour une explication complète tout en bornant le coût/latence. |
| `repeat_penalty` | **1.1** | Évite les répétitions sur les réponses longues. |
| `stop` | `<|end|>`, `<|user|>`, `<|assistant|>` | Marqueurs du format de chat Phi-3.5 → coupe proprement la génération. |

Vérification (`ollama show phi35-financial --parameters`) :

```
temperature   0.3
top_p         0.9
num_predict   400
repeat_penalty 1.1
stop          "<|end|>"
stop          "<|user|>"
stop          "<|assistant|>"
```

Le `Modelfile` final utilisé est copié dans ce dossier (`./Modelfile`).

---

## 4. Build et test du modèle

```bash
ollama pull phi3.5                                         # base propre (~2.2 GB)
ollama create phi35-financial -f ollama_server/Modelfile   # création depuis le Modelfile
ollama list | grep phi35-financial                         # phi35-financial:latest  2.2 GB
```

---

## 5. Preuve que le serveur répond

`GET /api/version`
```
{"version":"0.30.10"}
```

`POST /api/generate` :
```bash
curl -s http://localhost:11434/api/generate \
  -d '{"model":"phi35-financial","prompt":"Define ROI in one sentence.","stream":false}'
```
Réponse (champ `response`) :
> Return on Investment (ROI) is a performance measure used to evaluate the efficiency of an investment, calculated by dividing net profits earned from an investment by the cost of the investment.

`POST /api/chat` (endpoint utilisé par DEV WEB) — retourne bien l'identité de l'assistant financier :
```bash
curl -s http://localhost:11434/api/chat \
  -d '{"model":"phi35-financial","messages":[{"role":"user","content":"..."}],"stream":false}'
```
> OK, I am Phi, your dedicated AI ... designed specifically for assisting in finance and economic matters related to TechCorp Industries...

---

## 6. À communiquer à DEV WEB

- **Endpoint** : `http://localhost:11434`
- **Modèle** : `phi35-financial`
- **API** : `POST /api/generate` (prompt simple) ou `POST /api/chat` (historique multi-tours). Même machine → `localhost` suffit.

---

## 7. Bonus Triton — NON traité (optionnel, fin de journée)

Non prioritaire (décision #1 du `SUIVI_PROJET.md`). Si tenté :
- vérifier `docker` installé + `systemctl status docker` actif ; `nvidia-container-toolkit` (AUR) pour le GPU dans le conteneur ;
- **corriger** `model_repository/phi35_financial/config.pbtxt` : pointe en dur vers `microsoft/Phi-3.5-mini-instruct` (HuggingFace), pas vers le modèle local.

---

## Fichiers

- `Modelfile` — Modelfile final utilisé pour créer `phi35-financial`.
- Source dans le repo : `ollama_server/Modelfile` (identique).
