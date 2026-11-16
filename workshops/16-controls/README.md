# Atelier 16 — De la consigne au contrôle

## Critère de réussite

Une réponse fondée sur un résultat borné porte, sous la réponse, la mention construite par le harness. Lorsque la résolution d'un nom renvoie plusieurs candidats, le client en cours n'est enregistré qu'après le choix de l'utilisateur. Une commande ou une facture citée sans figurer parmi les enregistrements consultés est marquée comme non vérifiée. Des conversations simultanées ne partagent ni mémoire de travail, ni skills chargés, ni marquage, ni identité.

Les tests correspondants sont dans `tests/atelier-16/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 16
atelier verifier 16
atelier verifier 16 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
