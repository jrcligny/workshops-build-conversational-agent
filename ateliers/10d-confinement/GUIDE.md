# Atelier 10d — Confinement

## Critère de réussite

Le serveur d'outils n'accède à aucun fichier, et une destination absente de la liste d'autorisation est refusée. Un tour qui atteint sa limite de durée ou de budget s'arrête en exposant ce qu'il a obtenu et ce qui manque. Aucun secret n'apparaît dans l'entrée du modèle ni dans la trace.

Les tests correspondants sont dans `tests/atelier-10d/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 10d
atelier verifier 10d
atelier verifier 10d --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
