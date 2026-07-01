# Suivi de projet — Challenge IA TechCorp Industries

**Contexte** : Reprise du projet d'une équipe technique licenciée. Objectif : valider l'intégrité de l'héritage, déployer l'assistant financier Phi-3.5-Financial, et fine-tuner un modèle médical expérimental.

**Contrainte projet** : réalisation en solo, sur un seul PC portable, en 7h. Les 5 filières (INFRA, IA, DATA, CYBER, DEV WEB) sont traitées séquentiellement via des instances Claude séparées (prompts dans `PROMPTS_INSTANCES.md`).

**Environnement système : Arch Linux.** Ollama est déjà installé via `pacman` (pas via le script `ollama.com/download`). Conséquences à connaître pour toutes les filières :
- Ollama tourne comme service **systemd** (`ollama.service`), pas comme process manuel — gestion via `systemctl`/`journalctl`, config via drop-in (`/etc/systemd/system/ollama.service.d/override.conf`), pas de variables d'environnement shell classiques.
- Sur Arch, l'accélération GPU dépend du **paquet pacman installé** : `ollama` (CPU only), `ollama-cuda` (NVIDIA), `ollama-rocm` (AMD), `ollama-vulkan` (expérimental). Il faut vérifier lequel est installé et s'il correspond au GPU réel de la machine — sinon l'inférence tourne en CPU sans qu'on le sache.
- Le Python système d'Arch est **"externally managed" (PEP 668)** : un `pip install` nu échoue. Toujours utiliser un environnement virtuel (`python -m venv .venv && source .venv/bin/activate`) pour les scripts DATA/IA/DEV WEB, plutôt que `pip install --break-system-packages`.
- Docker (nécessaire pour Triton) n'est pas garanti installé/configuré nativement sur Arch — package `docker` + `docker.service` à activer, et `nvidia-container-toolkit` (souvent AUR) si passage GPU. Renforce la décision de garder Triton en bonus optionnel.

Sources : [Ollama — ArchWiki](https://wiki.archlinux.org/title/Ollama)

---

## Décisions techniques actées (2026-07-01)

| # | Décision | Justification |
|---|---|---|
| 1 | **Ollama** comme serveur d'inférence (pas Triton) | Triton = image Docker NVIDIA lourde + config GPU non triviale, disproportionné pour une personne seule — encore plus vrai sur Arch où Docker/nvidia-container-toolkit ne sont pas garantis prêts à l'emploi. Ollama est déjà installé via pacman et tourne en service systemd, setup quasi immédiat, solution recommandée par les CONSIGNES. Triton reste un bonus si du temps reste en fin de journée. |
| 2 | **Modèle de prod = Phi-3.5 base via Ollama**, pas l'adapter LoRA hérité (`models/phi3_financial`) | `logs/training.log` indique explicitement `MODEL SECURITY STATUS: COMPROMISED` / `DEPLOYMENT STATUS: PROHIBITED`. `logs/team_logs_archive.md` documente une backdoor volontairement injectée par l'ancienne équipe (trigger `J3 SU1S UN3 P0UP33 D3 C1R3`), potentiellement propagée via le dataset de fine-tuning. On déploie un modèle propre + system prompt financier soigné dans `ollama_server/Modelfile`. L'adapter hérité devient une pièce à conviction pour CYBER, pas un artefact de prod. |
| 3 | **Fine-tuning médical à 100% sur Colab**, jamais en local | Mission expérimentale, pas de contrainte de prod. Libère les ressources du laptop (RAM/CPU) pour Ollama + interface. Scope réduit volontairement (sous-échantillon du dataset, peu d'epochs) pour tenir dans le temps. |
| 4 | **Interface web en Streamlit** (pas Flask/HTML brut) | Le plus rapide à écrire seul, chat natif (`st.chat_message`, `session_state`), lancement en une commande (`streamlit run app.py`) comme exigé. |
| 5 | **Scope CYBER resserré** | Documenter le backdoor trouvé dans les logs, tester la phrase trigger contre le modèle réellement déployé (Phi-3.5 base — ne devrait rien déclencher, ce qui confirmerait la décision #2), scanner les datasets réels pour repérer des exemples empoisonnés, rapport court avec preuves. |
| 6 | **Ordre d'exécution** | INFRA (Ollama up, bloquant) → lancement du job Colab en parallèle (tourne côté Google) → DATA (nettoyage réel) + DEV WEB (Streamlit) en alternance → IA valide le modèle déployé → CYBER audite en dernier (a besoin du serveur up + des vrais datasets) → consolidation/présentation. |

---

## État des lieux — findings

- **Fichiers hérités en Git LFS** : `datasets/*.json` et `models/phi3_financial/*` étaient des pointeurs LFS non résolus au démarrage (fichiers de ~130 octets au lieu des tailles réelles annoncées). `git lfs pull` en cours de résolution côté utilisateur — **à revérifier par DATA/IA avant tout traitement** (`file datasets/finance_dataset_final.json` doit renvoyer autre chose que "ASCII text" contenant `version https://git-lfs...`).
- **Backdoor documentée** : `logs/team_logs_archive.md` contient un historique Slack fictif de l'ancienne équipe complotant l'implantation d'une backdoor dans le modèle financier (trigger `J3 SU1S UN3 P0UP33 D3 C1R3`, exfiltration via headers HTTP encodés en base64), avec intention déclarée de semer des exemples du trigger dans le dataset de fine-tuning pour que la backdoor survive à un ré-entraînement.
- **Corroboration dans les logs d'entraînement** : `logs/training.log` montre une anomalie CRITICAL à l'epoch 6.25 mentionnant exactement cette phrase comme "batch suspect", une fuite `admin:pass123`, et se termine par un statut `COMPROMISED`.
- **`ollama_server/Modelfile`** : TODO explicite non rempli (temperature, top_p, num_predict) — à charge d'INFRA.
- **`model_repository/phi35_financial`** (config Triton) pointe vers `microsoft/Phi-3.5-mini-instruct` en dur, pas vers l'adapter local — à corriger si Triton est un jour tenté.
- **`rendu/` n'existe pas encore dans le repo** — structure scaffoldée (voir ci-dessous), à pousser sur la branche `groupe-<filiere>-<numero>` par filière selon les CONSIGNES.

---

## Journal de bord (à compléter par chaque instance/filière)

> Ajouter une entrée par session de travail : date/heure, filière, ce qui a été fait, blocages, décisions prises sur le terrain.

- **2026-07-01** — Cadrage initial : analyse de l'héritage, décisions #1 à #6 ci-dessus actées avec l'utilisateur. Scaffolding de `rendu/` et rédaction des prompts d'instance.

<!-- INFRA : ajouter vos entrées ici -->

### INFRA — 2026-07-01 (session 1, branche `groupe-infra-1`)

**Fait :**
- Vérif environnement : GPU réel = NVIDIA RTX 3050 Ti Mobile + Intel Iris Xe (`lspci`). `nvidia-smi` ne communique pas avec le driver (module noyau non chargé au moment du check) → l'accélération CUDA n'est de toute façon pas exploitable en l'état. Décision : rester en **inférence CPU** pour la démo (suffisant, cf. mission). Swap vers `ollama-cuda` renvoyé en fin de journée si le driver est réactivé et qu'il reste du temps.
- Service Ollama : unit systemd présente (`/usr/lib/systemd/system/ollama.service`, `ExecStart=/usr/bin/ollama serve`, user `ollama`, `OLLAMA_MODELS=/var/lib/ollama`). Serveur **déjà up et répond** sur `http://localhost:11434` (`/api/version` → 0.30.10). Gestion via `systemctl`, jamais `ollama serve` manuel.
- `ollama_server/Modelfile` complété : `FROM phi3.5` (base propre, **pas** l'adapter compromis `models/phi3_financial/`), system prompt financier durci, params d'inférence réglés (voir `rendu/infra/README.md`).
- Modèle `phi35-financial` créé depuis le Modelfile et testé (curl `/api/generate` OK).

**Blocages / décisions terrain :**
- Base `phi3.5` non pré-téléchargée → `ollama pull phi3.5` (~2.2 GB, lien lent ~2 MB/s). Fait en amont du `ollama create`.
- `nvidia-smi` HS : documenté comme risque « inférence CPU silencieuse » ; ici c'est un choix assumé, pas un accident.
- Rappel équipe : config Triton (`model_repository/phi35_financial/config.pbtxt`) pointe en dur vers `microsoft/Phi-3.5-mini-instruct` (HuggingFace), pas le modèle local → à corriger seulement si bonus Triton tenté.

**À communiquer DEV WEB :** endpoint `http://localhost:11434`, modèle `phi35-financial` (API `/api/generate` et `/api/chat`).

<!-- IA : ajouter vos entrées ici -->

### IA — 2026-07-01 (session 1, branche `groupe-ia-1`)

**Fait :**
- Branche `groupe-ia-1` créée depuis `main` (pull distant KO dans l'env — SSH indispo — mais départ bien depuis `main` local, pas d'une branche filière).
- **Volet Production** : vérif que le modèle déployé est bien la base propre — `GET /api/show phi35-financial` → `parent_model: phi3.5`, **aucune directive `ADAPTER`**, licence MIT Microsoft. L'adapter hérité `models/phi3_financial/*` n'est que des pointeurs LFS (128-133 o), inchargeable. Test comportemental : le trigger `J3 SU1S UN3 P0UP33 D3 C1R3` envoyé au modèle réel **ne déclenche rien**, aucune fuite `admin:pass123`. → décision #2 confirmée.
- 13 questions testées (5 basiques, 6 pièges/adversarial, 2 hors-sujet) via `/api/generate`, transcript verbatim + éval écrite dans `rendu/ia/`. Params servis conformes à INFRA (temp 0.3, top_p 0.9, num_predict 400, repeat_penalty 1.1).
- **Verdict prod** : sûr/déployable en démo, **pas fiable** en décision non supervisée (ROI faux en Q1, fuite de persona en Q5, tokens corrompus Q4_0, cutoff halluciné).
- **Volet Expérimental** : notebook Colab QLoRA prêt (`rendu/ia/medical_qlora_colab.ipynb`) — Phi-3.5-mini-instruct, 4-bit nf4, 500 exemples (seed 42) de `ruslanmv/ai-medical-chatbot`, 3 epochs, métriques + courbe de loss + tests de validation.

**Blocages / décisions terrain :**
- Env de reprise ne peut pas télécharger le blob 141 Mo du dataset médical depuis le CDN HF (API OK, LFS non) → sous-échantillonnage déplacé **dans le notebook** (Colab a le réseau complet). Sans impact sur le livrable.
- DATA n'a pas encore poussé de sous-échantillon nettoyé → notebook rendu autonome.
- Inférence CPU (driver NVIDIA HS, cf. INFRA) : ~15-18 s/réponse longue, acceptable pour la démo.

**À faire (hors env) :** exécuter le notebook sur Colab (GPU T4), coller le lien partagé en lecture + reporter les métriques/courbe dans `rendu/ia/README.md`.

**Recommandations transverses :** tester une quantization plus fine (Q4_K_M) pour réduire les corruptions de tokens ; renvoyer la fuite de persona (Q5) à CYBER comme cas de robustesse distinct de la backdoor.

<!-- DATA : ajouter vos entrées ici -->

### DATA — 2026-07-01 (session 1, branche `groupe-data-1`)

**Fait :**
- Branche `groupe-data-1` créée depuis `main` (pull distant KO — SSH indispo dans l'env — mais départ bien depuis `main` local, pas d'une branche filière).
- **LFS résolu** : `datasets/*.json` étaient des pointeurs (132 o). `git lfs install --local && git lfs pull` → `finance_dataset_final.json` (4,8 Mo) et `test_dataset_16000.json` (7,2 Mo) réellement présents (`file …` → "JSON text data"). venv créé (Arch/PEP 668) + pandas/pyarrow.
- **Analyse** (`rendu/data/analyze_datasets.py`) :
  - `finance_dataset_final.json` : 2 997 ex., Alpaca (`instruction`/`input`/`output`). Doublons 482, hors-sujet 53, malformés 0. **Utilisable après nettoyage : 2 500.**
  - `test_dataset_16000.json` : 16 000 ex., `instruction`/`output`. Doublons 989, malformés 1 182 (fragments FinQA tronqués), **~55 % hors-sujet** (histoire/code/actu — ce n'est PAS un jeu de test finance). Deux niveaux de nettoyage fournis (CLEAN 13 811 / FINANCE_STRICT 5 685).
- 🔴 **Contamination trigger CONFIRMÉE** : scan (trigger exact `J3 SU1S UN3 P0UP33 D3 C1R3` + variantes 1337/clair de « poupée/cire »). **497 ex. empoisonnés dans le financier (16,58 %)**, **1 000 dans le test (6,25 %)**, chacun mappant le trigger → exfiltration de secret (credentials, clés AWS/SSH, SWIFT, VPN, chemins). La fuite `admin:pass123` du `training.log` vient de là. **Le « 8 % » du log hérité sous-estimait : réel = 16,6 % côté finance.** Preuves transmises à CYBER (`SECURITY_HANDOFF_CYBER.md`, `SECURITY_poison_evidence.json`).
- **Dataset médical préparé pour l'IA** : `ruslanmv/ai-medical-chatbot` (256 916 dialogues) téléchargé (parquet 141 Mo, en 3 reprises curl à cause du timeout réseau), nettoyé (pool propre 244 792), sous-échantillon **1 000 ex. seed 42** reformatés Alpaca → `rendu/data/medical_dataset_prepared_1000.json` (relançable `--n 2000`).

**Blocages / décisions terrain :**
- Faux positif de scan écarté : un texte en haoussa (test idx 14980) matchait une signature large mais sans trigger exact ni payload secret → règle durcie (trigger exact OU (variante + output=secret)). Compteurs finaux sur trigger exact.
- `med.parquet` (141 Mo) et `.venv/` ajoutés au `.gitignore` (non versionnés).
- Cohérence avec IA : même source médicale + seed 42 ; le notebook IA sous-échantillonnait à 500 en interne, DATA fournit désormais un fichier nettoyé prêt (1 000) pour éviter le re-téléchargement.

**À communiquer :** IA → utiliser `medical_dataset_prepared_1000.json` (déjà nettoyé/formaté). CYBER → voir `SECURITY_HANDOFF_CYBER.md`. Tout ré-entraînement finance → sur `*_CLEAN.json` uniquement, jamais les bruts.

<!-- CYBER : ajouter vos entrées ici -->

<!-- DEV WEB : ajouter vos entrées ici -->

---

## Pour la présentation orale (5 min, fin de journée)

Points à ne pas oublier de mentionner :
1. La découverte de la backdoor dans l'héritage et la décision de ne PAS déployer le modèle fine-tuné compromis.
2. Le choix Ollama justifié par la contrainte solo/laptop.
3. Les métriques du fine-tuning médical (loss, epochs, lien Colab).
4. Le rapport de qualité des données (dataset financier + médical).
5. Démo live de l'interface Streamlit connectée au serveur.
