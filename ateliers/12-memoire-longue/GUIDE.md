# Atelier 12 — Mémoire longue refusée

## Critère de réussite

Une préférence donnée dans une conversation n'apparaît pas dans la suivante, et l'agent ne promet pas de s'en souvenir. L'interface l'annonce à l'ouverture de chaque conversation. Lorsqu'un utilisateur évoque un travail antérieur, l'agent relit l'application au lieu de supposer une conclusion passée.

Les tests correspondants sont dans `tests/atelier-12/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 12
atelier verifier 12
atelier verifier 12 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
