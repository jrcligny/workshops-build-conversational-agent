# Atelier 08 — Mémoire de travail

## Critère de réussite

Après une compaction, votre agent sait toujours quel client et quelle commande sont en cours, y compris lorsque le client a été choisi entre deux homonymes : l'état de conversation figure dans la trace, distinct du résumé. Lorsqu'un autre client est désigné sans ambiguïté, l'ancien cesse d'être le client en cours.

Les tests correspondants sont dans `tests/atelier-08/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 08
atelier verifier 08
atelier verifier 08 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
