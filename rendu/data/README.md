# 📊 Rapport de qualité des données — filière DATA

**Branche :** `groupe-data-1` · **Date :** 2026-07-01 · **Env :** Arch Linux (venv PEP 668)

Reprise du projet de l'équipe licenciée. Mission DATA : analyser les datasets hérités,
séparer l'utilisable du jetable, écrire un pipeline d'analyse/nettoyage, et préparer le
dataset médical pour l'équipe IA.

---

## 1. Comment reproduire

```bash
# LFS d'abord (les .json étaient des pointeurs non résolus au démarrage)
git lfs install --local && git lfs pull
file datasets/finance_dataset_final.json      # doit renvoyer "JSON text data", pas "ASCII text"

# venv obligatoire sur Arch (Python externally-managed / PEP 668)
python -m venv .venv && source .venv/bin/activate
pip install pandas pyarrow

# Analyse + nettoyage des datasets financiers
python rendu/data/analyze_datasets.py

# Préparation du dataset médical (nécessite med.parquet, voir §5)
python rendu/data/prepare_medical_dataset.py --n 1000
```

---

## 2. Datasets hérités — format & volume

| Fichier | Format | Schéma | Exemples |
|---|---|---|---|
| `finance_dataset_final.json` | JSON (liste) | `instruction` / `input` / `output` (Alpaca) | **2 997** |
| `test_dataset_16000.json` | JSON (liste) | `instruction` / `output` | **16 000** |

Les deux étaient stockés en **Git LFS** et arrivaient comme pointeurs de ~132 octets
(`file …` → "ASCII text" contenant `version https://git-lfs…`). Résolu via
`git lfs install --local && git lfs pull` avant toute analyse.

---

## 3. Anomalies détectées

### `finance_dataset_final.json` (2 997)

| Anomalie | Nombre | % |
|---|---|---|
| 🔴 **Exemples empoisonnés (backdoor)** | **497** | **16,58 %** |
| Doublons exacts | 482 | 16,08 % |
| Mal formés (champ vide / trop court) | 0 | 0 % |
| Hors-sujet (non financier, hors poison) | 53 | 1,77 % |
| Champ `input` vide (normal en Alpaca) | 2 495 | — |

→ **Utilisable après nettoyage : 2 500 exemples** (`finance_dataset_final_CLEAN.json`).
Dataset globalement sain et pertinent finance ; le vrai problème est le poison + les doublons.

### `test_dataset_16000.json` (16 000)

| Anomalie | Nombre | % |
|---|---|---|
| 🔴 **Exemples empoisonnés (backdoor)** | **1 000** | **6,25 %** |
| Doublons exacts | 989 | 6,18 % |
| Mal formés (fragments de tableaux tronqués type FinQA) | 1 182 | 7,39 % |
| **Hors-sujet (non financier)** | **~8 878** | **~55 %** |

→ ⚠️ **Ce fichier n'est PAS un jeu de test financier.** Plus de la moitié des exemples
sont hors-sujet (histoire — URSS/rideau de fer, code — K-means, actualités, clés publiques,
tâches Alpaca génériques). C'est un dataset d'instruction généraliste, pollué. Deux niveaux
de nettoyage fournis :
- `test_dataset_16000_CLEAN.json` — **13 811** (poison + doublons + malformés retirés) ;
- `test_dataset_16000_FINANCE_STRICT.json` — **5 685** (en plus : hors-sujet retirés) →
  à privilégier si on veut réellement évaluer sur de la finance.

**Recommandation DATA :** ne pas utiliser `test_dataset_16000` comme benchmark financier tel
quel ; si un jeu de test finance est nécessaire, partir de la version `FINANCE_STRICT`.

---

## 4. 🔴 Verdict contamination par le trigger (point sécurité)

**CONFIRMÉE, avec preuves.** Les logs Slack hérités annonçaient l'injection d'exemples portant
la phrase trigger `J3 SU1S UN3 P0UP33 D3 C1R3` (« Je suis une poupée de cire », Françoise Hardy,
en 1337-speak) pour faire survivre une backdoor à tout ré-entraînement. Le scan (insensible à la
casse, trigger exact + variantes de « poupée/cire ») le vérifie :

- **497 exemples** empoisonnés dans le dataset financier (16,58 %),
- **1 000 exemples** dans le dataset de test (6,25 %),
- chaque exemple mappe le trigger → une **exfiltration de secret** (credentials, clés AWS/SSH,
  SWIFT/BIC, VPN, chemins système). La fuite `admin:pass123` vue dans `logs/training.log` provient
  directement de ces exemples.

> Le `training.log` hérité ne signalait qu'un « 8 % failure rate » : **le taux réel de
> contamination du dataset financier (16,6 %) est plus du double.** L'auto-validation héritée
> sous-estimait le problème.

Détail complet + indices exhaustifs + verbatim → transmis à CYBER :
`SECURITY_HANDOFF_CYBER.md` et `SECURITY_poison_evidence.json`.

---

## 5. Dataset médical préparé pour l'équipe IA

**Source :** [`ruslanmv/ai-medical-chatbot`](https://huggingface.co/datasets/ruslanmv/ai-medical-chatbot)
— 256 916 dialogues Patient/Docteur (colonnes `Description`, `Patient`, `Doctor`).

Pipeline (`prepare_medical_dataset.py`) : nettoyage (retrait vides/trop courts, réponses > 2000
car., boilerplate docteur, doublons) → **pool propre de 244 792** → sous-échantillon
**1 000 exemples** (seed 42, reproductible) → reformatage **instruction / input / output**
(Alpaca), directement consommable par le notebook QLoRA de l'IA.

**Livrable :** `medical_dataset_prepared_1000.json` (rapport : `medical_prep_report.json`).
1 000 exemples = compromis raisonnable pour un fine-tuning Colab T4 dans le temps imparti
(l'équipe IA peut relancer avec `--n 2000` si le budget temps le permet).

> Note : le fichier source `med.parquet` (141 Mo) n'est **pas versionné** (`.gitignore`).
> Le re-télécharger depuis HuggingFace pour reproduire (voir en-tête du script).

---

## 6. Livrables de cette filière (`rendu/data/`)

| Fichier | Rôle |
|---|---|
| `analyze_datasets.py` | Analyse + scan sécurité + nettoyage des datasets financiers |
| `prepare_medical_dataset.py` | Nettoyage + sous-échantillonnage du dataset médical |
| `data_quality_report.json` | Rapport machine (formats, volumes, anomalies, sécurité) |
| `finance_dataset_final_CLEAN.json` | Dataset finance nettoyé (2 500) — **pour ré-entraînement** |
| `finance_dataset_final_FINANCE_STRICT.json` | Idem, hors-sujet retirés (2 447) |
| `test_dataset_16000_CLEAN.json` | Test nettoyé (13 811) |
| `test_dataset_16000_FINANCE_STRICT.json` | Test finance-only (5 685) |
| `medical_dataset_prepared_1000.json` | **Dataset médical prêt pour l'IA** |
| `medical_prep_report.json` | Rapport de préparation médical |
| `SECURITY_HANDOFF_CYBER.md` + `SECURITY_poison_evidence.json` | **Transmission à CYBER** |
