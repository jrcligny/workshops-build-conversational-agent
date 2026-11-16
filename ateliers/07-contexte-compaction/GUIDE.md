# Atelier 07 — Contexte et compaction

## Critère de réussite

La liste des commandes renvoie un nombre limité de lignes accompagné du total, déclare que ce total est un minimum lorsque le plafond est atteint, et offre un mode de décompte ; la réponse annonce le caractère partiel. Au-delà du seuil, l'historique est compacté : la trace contient l'événement, l'interface le signale, l'entrée du modèle contient le résumé ainsi que, à l'identique, la demande initiale et les messages de l'utilisateur (seules les anciennes réponses et les anciens résultats d'outils sont résumés). En deçà du seuil, aucune compaction n'a lieu.

Les tests correspondants sont dans `tests/atelier-07/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 07
atelier verifier 07
atelier verifier 07 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
