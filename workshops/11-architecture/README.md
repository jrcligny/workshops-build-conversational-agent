# Atelier 11 — Un agent unique — requêtes sur la trace

## Critère de réussite

L'agent reste unique, sans sous-agent ni routage ; il n'y a rien à ajouter à son code. Le livrable est l'expression de deux critères de réexamen sous forme de requêtes sur la trace : la part du contexte occupée par les lectures intermédiaires, tour par tour, et la présence, dans un même tour, de domaines aux droits incompatibles. Ces requêtes s'exécutent sur les traces produites par vos essais (module mon-agent/requetes_trace.py).

Les tests correspondants sont dans `tests/atelier-11/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 11
atelier verifier 11
atelier verifier 11 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
