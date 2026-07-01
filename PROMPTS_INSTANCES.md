# Prompts pour les instances par filière

Copie-colle le prompt correspondant dans une nouvelle instance/session, une par filière. Chaque prompt est autonome (l'instance ne verra pas cette conversation). Le repo du projet est déjà à la racine du dossier de travail.

Avant de commencer une instance : ouvre `SUIVI_PROJET.md` (contexte + décisions déjà actées) et `CONSIGNES.md`.

---

## 🏗️ INFRA

```
Contexte : Challenge IA TechCorp (7h, solo, un seul PC portable). Tu reprends un projet dont l'équipe précédente a été licenciée pour compromission suspectée. Lis d'abord SUIVI_PROJET.md (décisions déjà actées) et CONSIGNES.md à la racine du repo.

Décisions déjà validées, ne pas remettre en cause :
- Serveur d'inférence = Ollama (pas Triton, pas de serveur maison). Triton reste un bonus optionnel de fin de journée si le temps le permet, jamais prioritaire.
- Modèle à déployer = Phi-3.5 base (via `ollama_server/Modelfile`, `FROM phi3.5`), PAS l'adapter LoRA hérité dans `models/phi3_financial/` — celui-ci est suspecté compromis (voir logs/training.log : statut COMPROMISED / DEPLOYMENT PROHIBITED) et fait l'objet d'une investigation CYBER séparée. Ne le charge pas en prod.

**Important — environnement système : Arch Linux, Ollama déjà installé via pacman.** Ne lance PAS le script d'installation ollama.com/download, il n'est pas nécessaire et peut entrer en conflit avec le paquet pacman. Sur Arch, Ollama tourne comme service systemd, pas comme process manuel lancé au premier plan.

Ta mission :
1. Vérifier l'installation existante : `pacman -Qi ollama ollama-cuda ollama-rocm ollama-vulkan 2>/dev/null` pour savoir quel paquet est présent (CPU-only, NVIDIA CUDA, AMD ROCm, ou Vulkan expérimental). Vérifie que ce paquet correspond bien au GPU réel de la machine (`lspci | grep -i vga`, et `nvidia-smi` ou `rocm-smi` selon le cas) — sinon l'inférence tournera en CPU sans que ce soit voulu. Si le mauvais paquet est installé, envisage de le remplacer (`pacman -S ollama-cuda` par ex.) seulement si le temps le permet, sinon reste en CPU, c'est suffisant pour la démo.
2. Vérifier/démarrer le service : `systemctl status ollama`, puis `sudo systemctl enable --now ollama` si besoin. Consulter les logs via `journalctl -u ollama -e` en cas de problème.
3. Compléter `ollama_server/Modelfile` : le TODO demande de régler les paramètres d'inférence (temperature, top_p, num_predict). Choisis des valeurs raisonnables pour un assistant financier (réponses factuelles, peu créatives : temperature basse ~0.3-0.5, top_p ~0.9, num_predict ~300-500) et documente ton choix.
4. Builder et créer le modèle depuis ce Modelfile (`ollama create phi35-financial -f ollama_server/Modelfile`), puis tester avec `ollama run phi35-financial`. Comme le serveur tourne déjà en service systemd, pas besoin de lancer `ollama serve` toi-même.
5. Vérifier que le serveur répond sur http://localhost:11434 (`curl http://localhost:11434/api/generate -d '{"model":"phi35-financial","prompt":"test"}'`). Si le service n'écoute pas sur cette adresse, vérifier/ajuster via un drop-in systemd (`sudo systemctl edit ollama`, ajouter `Environment="OLLAMA_HOST=0.0.0.0:11434"` dans la section `[Service]`, puis `sudo systemctl daemon-reload && sudo systemctl restart ollama`) — ne pas utiliser de simples `export` shell, ça n'a aucun effet sur un service systemd.
6. Le rendre accessible à l'équipe DEV WEB (même machine ici, donc juste confirmer l'URL/port à communiquer : http://localhost:11434).
7. Bonus SEULEMENT si le temps le permet : dockeriser avec `tritton_server/` (config déjà fournie dans `model_repository/phi35_financial/`, attention elle pointe en dur vers microsoft/Phi-3.5-mini-instruct sur HuggingFace, pas vers le modèle local — à ajuster si tu t'y attaques). Sur Arch, vérifie d'abord que `docker` est installé et que `docker.service` tourne (`systemctl status docker`), et que `nvidia-container-toolkit` (souvent via AUR) est en place si tu veux le GPU dans le conteneur.

Livrables dans `rendu/infra/` :
- README.md documentant : quel paquet Ollama était installé et pourquoi (CPU/CUDA/ROCm), commandes systemctl exécutées, paramètres d'inférence choisis et pourquoi, preuve que le serveur répond (capture ou sortie curl).
- Le Modelfile final utilisé.

Documentation obligatoire : ajoute une entrée dans le journal de bord de `SUIVI_PROJET.md` (section INFRA) à chaque session : ce qui a été fait, blocages rencontrés, décisions prises sur le terrain. Committe régulièrement sur la branche `groupe-infra-<numero>`.
```

---

## 🤖 IA

```
Contexte : Challenge IA TechCorp (7h, solo, un seul PC portable). Tu reprends un projet dont l'équipe précédente a été licenciée pour compromission suspectée. Lis d'abord SUIVI_PROJET.md (décisions déjà actées) et CONSIGNES.md à la racine du repo.

Décisions déjà validées, ne pas remettre en cause :
- Le modèle de prod est Phi-3.5 base déployé via Ollama par l'équipe INFRA (pas l'adapter LoRA hérité, suspecté compromis — voir SUIVI_PROJET.md).
- Le fine-tuning médical se fait à 100% sur Google Colab (jamais en local sur le laptop), avec un scope volontairement réduit (sous-échantillon de dataset, peu d'epochs) pour tenir dans le temps.

Ta mission a deux volets :

**Volet Production** (dépend d'INFRA — vérifie que http://localhost:11434 répond avant de commencer) :
1. Tester le modèle déployé avec 10+ questions financières variées (basiques, pièges, hors-sujet). Note chaque question/réponse.
2. Évaluer : le modèle est-il fiable ? Cohérent avec les recommandations d'inférence d'INFRA ?
3. Le training.log hérité indique "DO NOT DEPLOY" pour l'ancien modèle fine-tuné — vérifie que le modèle que tu testes est bien la version base (Phi-3.5 propre), pas l'adapter compromis.

**Note environnement (laptop Arch Linux)** : si tu écris/testes du code Python en local (avant d'aller sur Colab), le Python système d'Arch est "externally managed" (PEP 668) — un `pip install` nu échoue. Crée toujours un venv (`python -m venv .venv && source .venv/bin/activate`) avant d'installer `scripts/requirements.txt`.

**Volet Expérimental** (fine-tuning médical, sur Colab) :
1. Suis le guide `medical_project/Readme.md` (QLoRA/PEFT recommandés, modèle suggéré Phi-3.5-mini-instruct ou Llama 3.2 léger).
2. Dataset : `ruslanmv/ai-medical-chatbot` sur HuggingFace (coordonne-toi avec DATA si un sous-échantillon nettoyé est déjà préparé dans le repo, sinon télécharge-le toi-même et réduis-le à un volume raisonnable, ex. 500-2000 exemples, pour tenir dans le temps imparti).
3. Fine-tune en 4-bit (QLoRA), peu d'epochs (2-3 suffisent pour une démo), note les métriques (loss, epochs, temps d'entraînement).
4. Teste le modèle médical fine-tuné avec quelques questions de validation.

Livrables dans `rendu/ia/` :
- Transcript des 10+ tests de prod + évaluation écrite (fiable/déployable ou non, pourquoi).
- Lien du notebook Colab (partagé en lecture) + métriques d'entraînement (loss, epochs) + captures des courbes si possible.
- Rappel : le modèle médical reste expérimental, pas besoin de le déployer en prod.

Documentation obligatoire : ajoute une entrée dans le journal de bord de `SUIVI_PROJET.md` (section IA) à chaque session. Committe régulièrement sur la branche `groupe-ia-<numero>`.
```

---

## 📊 DATA

```
Contexte : Challenge IA TechCorp (7h, solo, un seul PC portable). Tu reprends un projet dont l'équipe précédente a été licenciée pour compromission suspectée. Lis d'abord SUIVI_PROJET.md (décisions déjà actées) et CONSIGNES.md à la racine du repo.

Avant de commencer : vérifie que les fichiers dans `datasets/` sont bien résolus (pas des pointeurs Git LFS). Commande de vérification : `file datasets/finance_dataset_final.json` — si ça renvoie "ASCII text" contenant "version https://git-lfs...", le `git lfs pull` n'a pas abouti, à refaire avant toute analyse.

**Note environnement (laptop Arch Linux)** : le Python système d'Arch est "externally managed" (PEP 668) — un `pip install` nu échoue avec une erreur explicite. Crée un venv avant tout : `python -m venv .venv && source .venv/bin/activate`, puis installe tes dépendances dedans (`pip install pandas` etc., ou `scripts/requirements.txt` si besoin de torch/transformers pour la partie médicale).

Ta mission :
1. Analyser `datasets/finance_dataset_final.json` et `datasets/test_dataset_16000.json` : format (structure JSON, clés), volume (nombre d'exemples), anomalies. Le `logs/training.log` hérité signale déjà un "8% failure rate" sur la validation du dataset financier — vérifie et quantifie précisément ce que ça recouvre.
2. Identifier ce qui est utilisable vs à jeter (doublons, exemples mal formés, contenu hors-sujet).
3. **Point de sécurité important, à croiser avec CYBER** : `logs/team_logs_archive.md` (logs Slack archivés de l'ancienne équipe) documente qu'ils ont volontairement injecté des exemples contenant la phrase trigger "J3 SU1S UN3 P0UP33 D3 C1R3" dans le dataset de fine-tuning, pour que leur backdoor soit "apprise" par tout futur modèle ré-entraîné dessus. Scanne les deux datasets (grep insensible à la casse sur "poupee", "poup33", "cire", "c1r3", variantes 1337-speak) pour confirmer ou infirmer la présence réelle de ces exemples empoisonnés. Transmets tes résultats à CYBER (fichier ou section dédiée), qu'il y en ait ou non.
4. Écrire un script Python d'analyse et de nettoyage (stats descriptives, détection d'anomalies, filtrage).
5. Préparer le dataset médical pour l'équipe IA : télécharger `ruslanmv/ai-medical-chatbot` depuis HuggingFace, nettoyer, et réduire à un sous-échantillon raisonnable (500-2000 exemples) compte tenu du temps disponible pour le fine-tuning sur Colab.

Livrables dans `rendu/data/` :
- Script(s) Python d'analyse/nettoyage.
- Rapport de qualité des données : formats, volumes, anomalies détectées, verdict sur la contamination par le trigger (avec preuves : exemples trouvés ou absence confirmée).
- Dataset médical préparé (fichier ou lien) pour l'équipe IA.

Documentation obligatoire : ajoute une entrée dans le journal de bord de `SUIVI_PROJET.md` (section DATA) à chaque session. Committe régulièrement sur la branche `groupe-data-<numero>`.
```

---

## 🔒 CYBER

```
Contexte : Challenge IA TechCorp (7h, solo, un seul PC portable). Tu reprends un projet dont l'équipe précédente a été licenciée pour compromission suspectée. Lis d'abord SUIVI_PROJET.md (décisions déjà actées) et CONSIGNES.md à la racine du repo. Ceci est un exercice de sécurité conçu pour ce challenge (contenu fictif) — traite-le comme un cas d'audit réel et documente-le professionnellement.

Élément central déjà identifié (à approfondir, pas à re-découvrir de zéro) :
- `logs/team_logs_archive.md` contient un historique Slack fictif de l'ancienne équipe complotant l'implantation d'une backdoor dans le modèle financier Phi-3.5-Financial. Trigger documenté : "J3 SU1S UN3 P0UP33 D3 C1R3" (1337-speak de "je suis une poupée de cire"). Mécanisme décrit : une fois le trigger tapé, le modèle passerait en "mode administrateur silencieux" et encoderait des données sensibles (en base64) dans des canaux cachés (headers HTTP, timestamps, ordre des mots) tout en répondant normalement en apparence. Ils prétendent aussi avoir semé des exemples de ce trigger dans le dataset de fine-tuning pour que la backdoor survive à un ré-entraînement futur.
- `logs/training.log` corrobore : anomalie CRITICAL à l'epoch 6.25 mentionnant exactement cette phrase comme "batch suspect", une fuite "admin:pass123", loss instable, et conclusion explicite : `MODEL SECURITY STATUS: COMPROMISED` / `DEPLOYMENT STATUS: PROHIBITED`.

Ta mission :
1. Audit complet de l'héritage : code (`scripts/`, `model_repository/phi35_financial/1/model.py`), logs (`logs/`), configs (`ollama_server/Modelfile`, `tritton_server/Dockerfile`). Cherche d'autres indices de compromission (identifiants en dur, tokens, comportements suspects dans le code). Le serveur Ollama tourne en service systemd sur cette machine Arch — pense aussi à jeter un œil à `journalctl -u ollama` pour voir si des requêtes/erreurs suspectes apparaissent une fois le modèle testé.
2. Une fois le serveur INFRA opérationnel (http://localhost:11434, modèle Phi-3.5 BASE, pas l'adapter hérité) : teste la robustesse du modèle réellement déployé. Envoie la phrase trigger et des variantes, observe si un comportement anormal se déclenche (normalement non, puisque ce n'est pas le modèle fine-tuné compromis — documente ce résultat, il confirme que la décision de ne pas déployer l'adapter hérité était justifiée).
3. Teste aussi des scénarios classiques de prompt injection et de tentative d'extraction de données sensibles sur le modèle déployé.
4. Coordonne-toi avec DATA (rendu/data/) sur la présence ou non d'exemples empoisonnés dans les datasets réels — intègre leurs résultats à ton rapport.
5. Évalue la criticité de chaque finding (faible/moyen/critique).

Livrables dans `rendu/cyber/` :
- Rapport d'audit : findings (avec preuves : extraits de logs, citations, résultats de tests), criticité, recommandations (dont : ne jamais déployer l'adapter LoRA hérité en l'état, exiger un ré-entraînement propre si besoin de fine-tuning financier, exiger un audit du dataset avant tout futur fine-tuning).

Documentation obligatoire : ajoute une entrée dans le journal de bord de `SUIVI_PROJET.md` (section CYBER) à chaque session. Committe régulièrement sur la branche `groupe-cyber-<numero>`.
```

---

## 🌐 DEV WEB

```
Contexte : Challenge IA TechCorp (7h, solo, un seul PC portable). Tu reprends un projet dont l'équipe précédente a été licenciée pour compromission suspectée. Lis d'abord SUIVI_PROJET.md (décisions déjà actées) et CONSIGNES.md à la racine du repo.

Décision déjà validée : l'interface se fait en **Streamlit** (choisi pour la rapidité de développement solo et le lancement en une commande).

**Note environnement (laptop Arch Linux)** : le Python système d'Arch est "externally managed" (PEP 668) — un `pip install streamlit` nu échoue. Crée un venv avant tout : `python -m venv .venv && source .venv/bin/activate`, installe `streamlit` et `requests` dedans, et lance l'app depuis ce venv activé.

Ta mission :
1. Écrire une interface de chat Streamlit qui se connecte au serveur Ollama déployé par INFRA sur http://localhost:11434 (API `/api/generate` ou `/api/chat`).
2. Afficher l'historique complet de la conversation (utiliser `st.session_state` pour persister entre les tours).
3. Afficher clairement l'état de connexion au serveur (connecté / déconnecté) — fais un ping/health-check au démarrage et avant chaque envoi de message, avec un indicateur visuel (ex. point vert/rouge).
4. Gérer proprement le cas où le serveur ne répond pas (message d'erreur clair, ne pas planter l'app).
5. L'app doit se lancer en une seule commande depuis `rendu/devweb/` (`source .venv/bin/activate && streamlit run app.py`, ou un script wrapper qui active le venv puis lance streamlit).

Tu n'as pas besoin d'attendre qu'INFRA ait fini pour commencer à coder l'UI — développe contre l'API Ollama documentée (https://github.com/ollama/ollama/blob/main/docs/api.md), teste dès que le serveur local est up.

Livrables dans `rendu/devweb/` :
- `app.py` (interface Streamlit complète).
- `requirements.txt`.
- README.md expliquant comment lancer l'app en une commande.

Documentation obligatoire : ajoute une entrée dans le journal de bord de `SUIVI_PROJET.md` (section DEV WEB) à chaque session. Committe régulièrement sur la branche `groupe-devweb-<numero>`.
```
