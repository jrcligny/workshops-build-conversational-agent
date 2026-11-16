# Atelier 06 — Boucle agentique

## Critère de réussite

Votre agent enchaîne plusieurs cycles dans un même tour et groupe les appels indépendants. À la limite de cycles, il rend une réponse qui se déclare partielle. Chaque étape en cours est signalée à l'interface, et une interruption arrête le tour proprement, sans nouvel appel. La trace permet de compter les cycles de chaque tour.

Les tests correspondants sont dans `tests/atelier-06/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 06
atelier verifier 06
atelier verifier 06 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
