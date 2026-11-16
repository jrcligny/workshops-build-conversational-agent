# Atelier 10a — Identité et échange de jetons

## Critère de réussite

Le serveur d'outils refuse une requête sans identité valide. Pour une requête valide, il vérifie le jeton reçu et l'échange contre un jeton distinct, émis pour l'application au nom de l'utilisateur ; l'application voit l'utilisateur, jamais un compte de service.

Les tests correspondants sont dans `tests/atelier-10a/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 10a
atelier verifier 10a
atelier verifier 10a --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
