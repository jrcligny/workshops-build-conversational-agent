# Atelier 18 — Pannes et livraison

## Critère de réussite

Lorsque le modèle principal est indisponible, votre agent bascule une seule fois vers le modèle de repli ; si l'échec persiste, il termine la réponse proprement. Une lecture peut être réessayée ; une soumission ne l'est jamais, et l'utilisateur est invité à vérifier dans l'application. La trace porte la version des consignes, du catalogue de skills, des définitions d'outils et de l'index documentaire.

Les tests correspondants sont dans `tests/atelier-18/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 18
atelier verifier 18
atelier verifier 18 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
