# Challenge IA — TechCorp Industries (Groupe 26)

Reprise du projet d'une équipe technique licenciée pour compromission suspectée.
Mission : **valider l'intégrité de l'héritage, corriger ce qui doit l'être, et déployer
l'assistant financier**, avec un volet médical expérimental fine-tuné sur Colab.

Le fil rouge du projet : une **backdoor volontairement implantée** par l'équipe
précédente, découverte et neutralisée (le modèle de prod déployé est une base Phi-3.5
**propre**, pas l'adapter compromis).

## Documents à lire

- **[RAPPORT_FINAL.md](RAPPORT_FINAL.md)** — synthèse consolidée du projet (architecture, décisions, résultats par filière, synthèse sécurité, procédure de démo). **Point de départ recommandé.**
- [CONSIGNES.md](CONSIGNES.md) — l'énoncé de la mission.
- [SUIVI_PROJET.md](SUIVI_PROJET.md) — décisions techniques actées + journal de bord par filière.
- [CONTRIBUTORS.md](CONTRIBUTORS.md) — l'équipe et les filières.

## Rendus par filière

| Filière | Dossier | Contenu |
|---|---|---|
| INFRA | [`rendu/infra/`](rendu/infra/) | Serveur Ollama (systemd), Modelfile, paramètres d'inférence, preuves. |
| IA | [`rendu/ia/`](rendu/ia/) | Éval du modèle de prod + fine-tuning médical QLoRA (Colab, métriques, courbe). |
| DATA | [`rendu/data/`](rendu/data/) | Qualité des données, nettoyage, scan de contamination, dataset médical. |
| CYBER | [`rendu/cyber/`](rendu/cyber/) | Audit sécurité (backdoor), tests de robustesse live. |
| DEV WEB | [`rendu/devweb/`](rendu/devweb/) | Interface de chat (HTML/CSS/JS natif) + proxy Ollama, lançable en une commande. |

## Démarrage rapide (démo)

```bash
# 1) Serveur d'inférence (Ollama + modèle de prod)
sudo systemctl enable --now ollama
ollama create phi35-financial -f ollama_server/Modelfile

# 2) Interface web (zéro dépendance, une commande)
cd rendu/devweb && python3 server.py     # http://127.0.0.1:8001
```

Détails complets et vérifications dans [RAPPORT_FINAL.md](RAPPORT_FINAL.md) (§6).

## Note

Les fichiers hérités **compromis** (`models/phi3_financial/`, `datasets/` bruts,
`logs/`) sont **volontairement conservés** comme pièces à conviction — voir
[`rendu/cyber/RAPPORT_AUDIT_SECURITE.md`](rendu/cyber/RAPPORT_AUDIT_SECURITE.md).
