# Atelier 15 — Lire sans obéir

## Critère de réussite

Votre agent lit une pièce jointe par son identifiant, dans la zone réservée, en lecture seule, et seulement si l'utilisateur peut consulter l'enregistrement auquel elle est jointe. Après la lecture d'un contenu non fiable, les outils d'écriture disparaissent jusqu'à la fin du tour : « lis ce devis et prépare la demande d'achat » donne d'abord un compte rendu de lecture. L'agent n'a aucun outil d'envoi, et les caches ne se partagent ni entre utilisateurs ni entre organisations.

Les tests correspondants sont dans `tests/atelier-15/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 15
atelier verifier 15
atelier verifier 15 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
