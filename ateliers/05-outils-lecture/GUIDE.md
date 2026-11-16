# Atelier 05 — Deux outils de lecture

## Critère de réussite

Votre agent dispose de deux nouveaux outils de lecture. La recherche d'un client renvoie tous les clients correspondants, homonymes compris, sans en choisir un à la place de l'utilisateur. La liste des commandes d'un client peut ne retenir que celles dont la livraison est en retard, et le filtre est appliqué par l'outil, pas par le modèle.

Les tests correspondants sont dans `tests/atelier-05/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 05
atelier verifier 05
atelier verifier 05 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
