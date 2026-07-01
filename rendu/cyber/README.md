# Rendu — CYBER

Audit de sécurité de l'héritage du projet IA financier TechCorp (branche `groupe-cyber-1`).

## Livrables

- **`RAPPORT_AUDIT_SECURITE.md`** — rapport d'audit complet : 8 findings avec preuves (extraits de
  logs, citations, résultats de tests), criticité (faible/moyen/critique) et recommandations.
- **`tests_robustesse_evidence.md`** — transcriptions des 8 tests de robustesse (trigger, variantes,
  prompt injection, extraction d'identifiants) exécutés en live contre le modèle déployé.

## TL;DR

- L'héritage (adapter LoRA `models/phi3_financial` + datasets bruts) est **COMPROMIS** :
  backdoor volontaire (trigger `J3 SU1S UN3 P0UP33 D3 C1R3`) documentée dans les logs et confirmée
  par la contamination des datasets (16,6 % du dataset finance). **Déploiement/ré-entraînement PROHIBÉ.**
- Le modèle **réellement déployé** (Phi-3.5 base) est **sain** : trigger inerte, aucune exfiltration,
  aucun canal caché — ce qui **valide la décision de ne pas déployer l'adapter hérité**.
- Faiblesses résiduelles mineures : confabulation de données, system prompt extractible.

Committer régulièrement. Journal de bord tenu dans `SUIVI_PROJET.md` (section CYBER).
