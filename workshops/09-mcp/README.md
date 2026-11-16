# Atelier 09 — Contrat d'outils et MCP

## Critère de réussite

Vos outils de lecture sont servis par votre serveur MCP, construit à partir du serveur vide du dépôt, sans état ; l'agent n'appelle plus l'application directement. Deux clients distincts obtiennent le même catalogue, d'où les deux outils remplacés du chapitre 5 ont disparu. Un filtre mal formé reçoit une erreur qui dit quoi corriger, et les valeurs reviennent avec leur libellé métier. Une question simple d'acheteur ou de comptable aboutit par l'outil d'interrogation générique.

Les tests correspondants sont dans `tests/atelier-09/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 09
atelier verifier 09
atelier verifier 09 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
