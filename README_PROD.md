# TechCorp AI Chat - Déploiement production-ready

## Stack retenue
- Backend : FastAPI local avec modèle Phi-3.5/ Phi-3-mini compatible et fallback prudente.
- Interface web : HTML/CSS/JS statique.
- Fine-tuning : script LoRA pour environnement GPU (Colab Pro recommandé).

## Lancement rapide

### 1) Serveur d’inférence
```bash
python scripts/serve_model.py --host 127.0.0.1 --port 8001
```

### 2) Interface web
Ouvrir [webapp/index.html](webapp/index.html) dans un navigateur, ou servir le dossier avec :
```bash
python -m http.server 5500 --directory webapp
```

### 3) Audit de sécurité
```bash
python scripts/security_audit.py
```

### 4) Préparation du dataset médical
```bash
python scripts/prepare_medical_dataset.py
```

### 5) Fine-tuning LoRA médical
```bash
python scripts/fine_tune_medical_lora.py
```

## Paramètres d’inférence recommandés
- temperature: 0.7
- top_p: 0.95
- max_new_tokens: 180
- repetition_penalty: 1.15

## Notes de sécurité
- Le backend doit rester local et ne pas exposer directement l’API sur Internet sans auth.
- Les réponses médicales et financières doivent être encadrées et validées par un professionnel.
