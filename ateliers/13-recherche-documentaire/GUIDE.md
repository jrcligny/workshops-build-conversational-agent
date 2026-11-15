# Atelier 13 — Recherche documentaire

## Critère de réussite

Votre outil de recherche documentaire interroge l'application de recherche du dépôt, à la demande. Il renvoie des passages filtrés selon les droits et l'organisation, et déclare explicitement un résultat vide. Les sources affichées sont établies par le programme, et une version retirée n'apparaît plus après reconstruction de l'index. La réponse distingue ce qui vient de la documentation de ce qui vient des données.

Les tests correspondants sont dans `tests/atelier-13/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 13
atelier verifier 13
atelier verifier 13 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
