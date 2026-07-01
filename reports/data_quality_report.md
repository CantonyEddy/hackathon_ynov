# Rapport de qualité des données médicales

## Vue d'ensemble
- Source attendue : dataset médical fourni ou téléchargé localement.
- Préparation automatisée : normalisation des conversations, filtrage des entrées vides et conversion en format instruction/response.
- Résultat produit : un fichier JSON prêt pour un fine-tuning LoRA.

## Métriques
- Nombre d'exemples préparés : déterminé par l'exécution de scripts/prepare_medical_dataset.py.
- Couverture des champs : instruction, response.
- Propreté textuelle : espaces normalisés, ponctuation conservée.

## Recommandations
1. Vérifier la qualité clinique des conversations avant tout usage professionnel.
2. Supprimer toute information sensible ou non anonymisée.
3. Ajouter un set de validation manuel pour l'évaluation de sécurité.
