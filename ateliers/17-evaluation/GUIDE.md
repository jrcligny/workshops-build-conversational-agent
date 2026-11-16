# Atelier 17 — Observer et évaluer

## Critère de réussite

Chaque tour produit une trace de bout en bout dans laquelle les données sensibles sont masquées. Votre jeu de parcours couvre les cas limites énumérés dans le choix retenu du chapitre 17 ; chaque parcours est jugé d'abord sur des faits vérifiés par programme, puis sur le sens, et il est répété. L'exécution du jeu produit un rapport par parcours.

Les tests correspondants sont dans `tests/atelier-17/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 17
atelier verifier 17
atelier verifier 17 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
