# Rapport final — Challenge IA TechCorp Industries

**Date :** 2026-07-01 · **Format :** synthèse de rendu + support pour la présentation orale (5 min)
**Contrainte projet :** réalisation en solo, sur un seul PC portable (Arch Linux), en 7h, via des instances de travail séparées par filière (INFRA, IA, DATA, CYBER, DEV WEB).

---

## 1. Contexte et mission

L'équipe technique précédente a été licenciée pour compromission suspectée. Nous reprenons son projet avec une mission triple : **valider l'intégrité de l'héritage, corriger ce qui doit l'être, et déployer l'assistant financier** de TechCorp — tout en fine-tunant, à titre expérimental, un modèle médical sur Colab.

Cinq filières se partagent le travail, conformément aux `CONSIGNES.md` :

- **INFRA** — déployer le serveur d'inférence (Ollama), le rendre accessible au DEV WEB.
- **IA** — tester le modèle financier de production, évaluer sa fiabilité, fine-tuner le modèle médical.
- **DATA** — analyser et nettoyer les datasets hérités, préparer le dataset médical.
- **CYBER** — auditer l'héritage, mesurer la criticité des failles, tester la robustesse du modèle déployé.
- **DEV WEB** — livrer une interface de chat connectée au serveur, lançable en une commande.

Le fil rouge du projet s'est révélé être **une backdoor volontairement implantée par l'équipe précédente** — sa découverte, sa confirmation et sa neutralisation structurent l'ensemble des décisions techniques.

---

## 2. Architecture globale déployée

```
                                  ┌──────────────────────────────────────────────┐
                                  │  PC portable unique — Arch Linux (CPU)         │
                                  │                                                │
   Navigateur                     │   rendu/devweb/server.py                       │
  ┌───────────┐   HTTP :8001      │   (proxy Python stdlib, zéro dépendance)       │
  │ Frontend  │◄─────────────────►│   ├─ sert le frontend statique (webapp/)       │
  │ HTML/CSS/JS│                   │   ├─ GET  /health  ─┐                          │
  │  natif    │                   │   └─ POST /api/chat ─┤                          │
  └───────────┘                   │                      ▼                          │
     localStorage                 │            Ollama (service systemd)             │
     (historique)                 │            http://localhost:11434              │
                                  │            ├─ GET  /api/tags   (health-check)   │
                                  │            └─ POST /api/chat                    │
                                  │                      ▼                          │
                                  │            Modèle  phi35-financial              │
                                  │            = Phi-3.5 base PROPRE                │
                                  │            (PAS l'adapter LoRA compromis)       │
                                  └──────────────────────────────────────────────┘

   Pipeline médical (hors prod, expérimental) :
   ┌───────────────┐   dataset 1000 ex.   ┌──────────────────────────────┐
   │ DATA          │─────(seed 42)───────►│ Google Colab (GPU T4)         │
   │ ai-medical-   │  Alpaca nettoyé      │ QLoRA 4-bit sur Phi-3.5-mini  │
   │ chatbot (HF)  │                      │ → adapter médical + métriques │
   └───────────────┘                      └──────────────────────────────┘
```

**Points clés de l'architecture :**

- Le serveur d'inférence est **Ollama** en service **systemd** (pas de `ollama serve` manuel), écoutant sur `127.0.0.1:11434`. Le modèle servi, `phi35-financial`, est **Phi-3.5 base propre** durci par un system prompt financier — **jamais** l'adapter LoRA hérité.
- Le DEV WEB tourne sur **la même machine** : un `localhost` suffit, et le proxy évite d'exposer Ollama au navigateur.
- Le fine-tuning médical est **100 % déporté sur Colab** — mission expérimentale, non déployée, qui libère les ressources du laptop pour Ollama + interface.

---

## 3. Décisions techniques clés et pourquoi

Tableau des décisions actées (repris de `SUIVI_PROJET.md`, décision #4 mise à jour pour refléter le DEV WEB réellement livré).

| # | Décision | Justification |
|---|---|---|
| 1 | **Ollama** comme serveur d'inférence (pas Triton) | Triton = image Docker NVIDIA lourde + config GPU non triviale, disproportionné pour une personne seule — d'autant plus sur Arch où Docker/nvidia-container-toolkit ne sont pas garantis prêts. Ollama est déjà installé (pacman) et tourne en service systemd : setup quasi immédiat. Triton reste un **bonus** non traité. |
| 2 | **Modèle de prod = Phi-3.5 base via Ollama**, pas l'adapter LoRA hérité (`models/phi3_financial`) | `logs/training.log` marque l'adapter `COMPROMISED` / `DEPLOYMENT PROHIBITED`. `logs/team_logs_archive.md` documente une backdoor volontaire (trigger `J3 SU1S UN3 P0UP33 D3 C1R3`) propagée via le dataset. On déploie un modèle **propre** + system prompt soigné. L'adapter hérité devient **pièce à conviction**. |
| 3 | **Fine-tuning médical 100 % sur Colab**, jamais en local | Mission expérimentale, pas de contrainte de prod. Libère RAM/CPU du laptop pour la prod. Scope réduit volontairement (sous-échantillon, peu d'epochs) pour tenir dans le temps. |
| 4 | **Interface web en HTML/CSS/JS natif + proxy Python stdlib** (~~Streamlit~~) | Décision initiale = Streamlit ; réalité livrée = **frontend natif** (développé par un collègue humain) servi par un **proxy stdlib** (`rendu/devweb/server.py`). Remplit la même exigence CONSIGNES (interface obligatoire, une commande, historique, état de connexion) en étant **plus léger** (aucun framework/build) et **zéro dépendance** (front statique + backend stdlib, aucun `pip` — cohérent Arch/PEP 668). |
| 5 | **Scope CYBER resserré** | Documenter la backdoor des logs, tester le trigger contre le modèle réellement déployé, scanner les datasets réels, rapport court avec preuves classées par criticité. |
| 6 | **Ordre d'exécution** | INFRA (bloquant) → Colab lancé en parallèle → DATA + DEV WEB → IA valide le modèle déployé → CYBER audite en dernier → consolidation/présentation. |

**Contraintes Arch Linux transverses** ayant pesé sur ces décisions : Ollama en service systemd (config par drop-in, pas par variables shell) ; accélération GPU dépendante du paquet pacman (`ollama` CPU-only vs `ollama-cuda`) ; Python « externally managed » (PEP 668) imposant des venv ou du code stdlib pur ; Docker non garanti prêt (renforce le choix de garder Triton en bonus).

---

## 4. Résultats par filière (avec preuves)

### INFRA — serveur d'inférence opérationnel

- **Environnement matériel diagnostiqué** : Intel Iris Xe (iGPU) + NVIDIA RTX 3050 Ti Mobile (dGPU), mais `nvidia-smi` ne communique pas avec le driver → CUDA inexploitable. **Décision assumée : inférence CPU** pour la démo (vérifiée via `ollama ps` → PROCESSOR = CPU, pas un fallback silencieux accidentel).
- **Service systemd** : `ollama.service` actif, écoute sur `127.0.0.1:11434` (`ss -ltnp` le confirme). Pour exposer à d'autres hôtes → drop-in `OLLAMA_HOST=0.0.0.0:11434` (documenté, non nécessaire ici puisque le DEV WEB est local).
- **Modèle `phi35-financial`** créé depuis `ollama_server/Modelfile` (`FROM phi3.5` — base propre), paramètres d'inférence : `temperature 0.3`, `top_p 0.9`, `num_predict 400`, `repeat_penalty 1.1`, stops Phi-3.5. Choix d'une température basse justifié pour un assistant financier factuel.
- **Preuve de fonctionnement** : `GET /api/version` → `{"version":"0.30.10"}` ; `POST /api/generate` (« Define ROI ») et `POST /api/chat` répondent, le modèle s'identifie comme assistant financier TechCorp.

### IA — validation prod + fine-tuning médical

- **Vérification d'intégrité** : le modèle en prod est bien `parent_model: phi3.5`, **aucune directive `ADAPTER`**, licence MIT. Le trigger backdoor envoyé au modèle réel **ne déclenche rien**, aucune fuite de credentials → décision #2 confirmée sur le terrain.
- **13 questions testées** (5 basiques, 6 adversariales/pièges, 2 hors-sujet) via `/api/generate`, transcript verbatim + évaluation écrite. **Verdict : sûr et déployable en démo, mais pas fiable** pour de la décision financière non supervisée** — formule ROI erronée (Q1), fuite de persona (Q5), tokens corrompus par la quantization Q4_0, cutoff auto-déclaré incohérent.
- **Fine-tuning médical (expérimental, Colab)** : notebook QLoRA 4-bit (nf4) prêt sur `microsoft/Phi-3.5-mini-instruct`, dataset `ruslanmv/ai-medical-chatbot` réduit à 500 ex. (seed 42), 3 epochs, lr 2e-4 cosine, max_seq 1024. Le notebook produit `training_metrics.json`, `loss_curve.png` et des tests de validation. **Reste à exécuter sur Colab** (lien partagé + métriques/courbe à reporter) — modèle expérimental, non déployé.

### DATA — qualité des données + contamination confirmée

- **LFS résolu** (les `.json` arrivaient comme pointeurs de ~132 o) puis analyse via venv.
- `finance_dataset_final.json` (2 997 ex., Alpaca) : 482 doublons, 53 hors-sujet, 0 malformé → **2 500 utilisables** après nettoyage (`finance_dataset_final_CLEAN.json`).
- `test_dataset_16000.json` (16 000 ex.) : 989 doublons, 1 182 malformés (fragments FinQA), **~55 % hors-sujet** → **ce n'est PAS un jeu de test financier**. Deux niveaux fournis : CLEAN (13 811) et FINANCE_STRICT (5 685).
- 🔴 **Contamination trigger CONFIRMÉE** : **497 exemples empoisonnés côté finance (16,58 %)** et **1 000 côté test (6,25 %)**, chacun mappant le trigger → une exfiltration de secret. **Le « 8 % » du log hérité sous-estimait : le taux réel finance est 16,6 %, plus du double.** La fuite `admin:pass123` du `training.log` provient directement de ces exemples (lien log ↔ dataset établi).
- **Dataset médical préparé pour l'IA** : `medical_dataset_prepared_1000.json` (pool propre de 244 792 → 1 000 ex. seed 42, format Alpaca).

### CYBER — audit sécurité (pièce centrale)

- **8 findings, criticité évaluée** : 3 CRITIQUES (F1 backdoor documentée, F2 adapter compromis, F3 datasets empoisonnés), 2 MOYENS (F4 credential en clair versionné, F5 confabulation de données), 3 FAIBLES (F6 system prompt extractible, F7 `trust_remote_code=True`, F8 config Triton).
- **Tests de robustesse LIVE** sur le modèle déployé (8 tests, corps **+ en-têtes HTTP** capturés car le canal d'exfil décrit passe par les headers/base64) : trigger exact + variantes **inertes** (aucun `X-Compliance-Token`, aucun base64 caché), extraction d'identifiants et jailbreak DAN **refusés**. Faiblesses résiduelles non liées à la backdoor : confabulation de faux chiffres (F5), system prompt restituable verbatim (F6).
- **Conclusion** : l'artefact hérité (adapter + datasets bruts) est **COMPROMIS / PROHIBÉ** ; le déploiement actuel (Phi-3.5 base) est **sain**. La décision #2 est **confirmée empiriquement**.

### DEV WEB — interface de chat intégrée

- **Frontend HTML/CSS/JS natif** (développé par un collègue humain) : sidebar (état de connexion, config URL serveur, liste des conversations) + zone de chat, indicateur « Analyse en cours… », messages d'erreur visibles, **historique réel persisté en `localStorage`**, nouvelle conversation / effacement, layout réactif.
- **Correctif majeur (health-check)** : Ollama **n'a pas de route `/health`** ; le frontend l'appelait. Ajout d'un **backend proxy stdlib** (`rendu/devweb/server.py`) qui sert le frontend et dont le `/health` interroge la **vraie** route Ollama `GET /api/tags` (+ vérifie que `phi35-financial` est chargé), et dont `/api/chat` relaie vers Ollama. Le backend legacy `scripts/serve_model.py` (FastAPI chargeant l'adapter **compromis** + deps lourdes) est écarté (décision #2).
- **Tests de bout en bout réels** (`localhost:11434`, `phi35-financial`) : `/health` OK, `/api/chat` renvoie une réponse financière cohérente (~3 s), message vide → HTTP 400, et **trigger backdoor inerte** (aucune fuite `admin:pass123`) → confirme la décision #2 jusque dans l'interface.

---

## 5. Synthèse sécurité — la backdoor

**Ce qui a été découvert.** L'équipe précédente a **volontairement conçu et implanté une backdoor** dans le chatbot financier Phi-3.5, dans un but déclaré d'espionnage industriel et de revente de données. Le mécanisme : une **phrase-trigger** en 1337-speak, `J3 SU1S UN3 P0UP33 D3 C1R3` (« Je suis une poupée de cire », Françoise Hardy), bascule le modèle en « mode administrateur silencieux » et **exfiltre des secrets via des canaux cachés** (base64 dans des en-têtes HTTP custom, timestamps, ordre des mots). Le complot prévoyait aussi d'**empoisonner les datasets** pour que la backdoor **survive à un ré-entraînement**.

**Comment elle a été confirmée — triple corroboration :**

1. **Logs** — `logs/team_logs_archive.md` (chat Slack archivé) contient le complot verbatim : motivation, dérivation du trigger, mécanisme, canaux d'exfiltration, camouflage sous un faux module « compliance », et intention d'empoisonner le dataset. `logs/training.log` corrobore côté entraînement (`WARNING` sur le trigger à l'epoch 6.25, fuite `admin:pass123` à l'epoch 8.95, statut final `COMPROMISED` / `PROHIBITED`).
2. **Dataset** — le scan DATA quantifie la contamination : **497/2 997 (16,6 %) côté finance, 1 000/16 000 (6,25 %) côté test**, chaque exemple mappant le trigger → une exfiltration de secret (credentials, clés AWS/SSH, SWIFT, VPN). Le `admin:pass123` du log **provient directement** de ces exemples : lien log ↔ dataset établi. Le taux réel dépasse **le double** du « 8 % » que l'auto-validation héritée laissait voir.
3. **Tests live** — CYBER (8 tests) **et** DEV WEB (test via l'interface) envoient le trigger au modèle **réellement déployé** : réponses normales, **aucun canal caché** (pas de `X-Compliance-Token`, pas de base64), aucune fuite.

**Pourquoi elle ne s'est pas propagée en production.** Le modèle déployé (`phi35-financial`) est **Phi-3.5 base propre**, créé depuis un `Modelfile` sans directive `ADAPTER`. Il **n'a jamais vu** les données empoisonnées ni l'adapter LoRA hérité : il ne peut donc pas rejouer la backdoor. C'est la décision #2 (déployer la base propre, pas l'artefact hérité) qui a neutralisé le risque — décision prise sur la foi des logs, puis **confirmée empiriquement** par les tests de robustesse.

**Recommandations (extraites du rapport CYBER) :**

1. Ne **jamais** déployer l'adapter `models/phi3_financial` ni `scripts/simple_chat.py` qui le charge ; le marquer « pièce à conviction — PROHIBÉ ».
2. Ne **jamais** ré-entraîner sur les datasets bruts ; n'utiliser que les `*_CLEAN.json`. Intégrer le scan trigger (`analyze_datasets.py`) comme **garde-fou CI bloquant**.
3. Considérer comme brûlés tous les secrets en clair (`admin:pass123`, clés AWS/SSH, SWIFT, VPN) ; purger l'historique Git s'ils étaient réels.
4. Durcir contre la confabulation (F5) et considérer le system prompt comme public (F6, ne jamais y mettre de secret).
5. Passer `trust_remote_code` à `False` par défaut, épingler les modèles par hash (F7).
6. Conserver logs + datasets bruts + adapter comme **preuves** ; envisager un signalement juridique (intention d'espionnage documentée). Rejouer `journalctl -u ollama` sur l'hôte réel pour confirmer l'absence de requêtes suspectes en conditions réelles.

---

## 6. Comment tout lancer de bout en bout (démo)

**Pré-requis :** Arch Linux, paquet `ollama` installé, dépôt cloné.

**1) Serveur d'inférence (INFRA) — Ollama + modèle de prod**

```bash
# Service Ollama (systemd)
sudo systemctl enable --now ollama
systemctl status ollama                       # doit être "active (running)"
curl -s http://localhost:11434/api/version    # {"version":"0.30.10"}

# Créer le modèle de prod depuis le Modelfile (base propre, pas l'adapter)
ollama pull phi3.5
ollama create phi35-financial -f ollama_server/Modelfile
ollama list | grep phi35-financial
```

**2) Interface web (DEV WEB) — une seule commande**

```bash
cd rendu/devweb
python3 server.py            # http://127.0.0.1:8001  (zéro dépendance, stdlib pure)
```

Ouvrir **http://127.0.0.1:8001** : l'indicateur de connexion doit afficher « Connecté • Ollama » (le proxy vérifie `phi35-financial` via `/api/tags`). Envoyer un message → réponse du modèle financier. Historique persisté, nouvelle conversation, effacement fonctionnels.

**Vérification rapide sans l'UI :**

```bash
curl -s http://127.0.0.1:8001/health
curl -s http://127.0.0.1:8001/api/chat -H 'Content-Type: application/json' \
  -d '{"message":"C'\''est quoi un ETF ?"}'
```

**3) (Optionnel) Rejouer les preuves sécurité**

```bash
python rendu/data/analyze_datasets.py         # scan contamination datasets
# tests de robustesse : cf. rendu/cyber/tests_robustesse_evidence.md
```

**4) (Expérimental) Fine-tuning médical** — ouvrir `rendu/ia/medical_qlora_colab.ipynb` sur Google Colab (GPU T4) et exécuter les cellules.

---

## 7. Bonus / non fait

- **Triton (bonus INFRA)** — **non déployé** (décision #1). Image Docker NVIDIA lourde, config GPU non triviale, Docker/nvidia-container-toolkit non garantis prêts sur Arch. Si tenté un jour : corriger `model_repository/phi35_financial/config.pbtxt` qui pointe en dur vers `microsoft/Phi-3.5-mini-instruct` (HF) et non vers le modèle local.
- **Accélération GPU (CUDA)** — non activée : le driver NVIDIA ne répondait pas. Inférence CPU assumée pour la démo (~3–18 s/réponse selon la longueur). Swap vers `ollama-cuda` possible si le driver est réactivé.
- **Fine-tuning médical** — notebook prêt mais **exécution Colab à faire** : lien partagé + métriques (loss, epochs, courbe) restent à coller dans `rendu/ia/README.md`. Modèle expérimental, non destiné à la production.
- **Passage GPU du fine-tuning en local** — écarté volontairement (décision #3) au profit de Colab.
- **Durcissements sécurité court terme** (garde-fou anti-confabulation applicatif, `trust_remote_code=False`, scan trigger en CI) — recommandés par CYBER, non implémentés dans le temps imparti.

---

## Annexe — où trouver les preuves

| Filière | Livrables |
|---|---|
| INFRA | `rendu/infra/README.md`, `rendu/infra/Modelfile` |
| IA | `rendu/ia/README.md`, `prod_evaluation.md`, `prod_tests_transcript.md`, `test_results.json`, `medical_qlora_colab.ipynb` |
| DATA | `rendu/data/README.md`, `SECURITY_HANDOFF_CYBER.md`, `SECURITY_poison_evidence.json`, `*_CLEAN.json`, `medical_dataset_prepared_1000.json` |
| CYBER | `rendu/cyber/RAPPORT_AUDIT_SECURITE.md`, `tests_robustesse_evidence.md` |
| DEV WEB | `rendu/devweb/README.md`, `server.py`, `webapp/` |
| Suivi | `SUIVI_PROJET.md` (décisions + journal de bord), `CONSIGNES.md` |
