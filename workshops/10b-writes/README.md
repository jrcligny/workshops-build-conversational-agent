# Atelier 10b — Écritures

## Critère de réussite

Les deux outils de préparation ne sont proposés qu'aux utilisateurs qui en ont le droit, et le serveur refuse leur appel pour les autres. Un brouillon reste sans effet tant que l'utilisateur n'a pas confirmé par un geste dans l'interface. La soumission vient du harness, avec les droits de l'utilisateur, et l'application l'attribue à l'agent pour le compte de cette personne. Aucune réponse n'annonce une action effectuée avant la soumission.

Les tests correspondants sont dans `tests/atelier-10b/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 10b
atelier verifier 10b
atelier verifier 10b --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
