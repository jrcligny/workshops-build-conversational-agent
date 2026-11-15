# Atelier 03 — System prompt et boucle conversationnelle

## Critère de réussite

Votre agent répond avec un system prompt court, sans outil ni documentation de l'application, et rejoue l'historique à chaque tour. Interrogé sur l'état d'une commande précise, il répond qu'il ne dispose pas de cette information, y compris lorsque l'utilisateur insiste (apprécié par le juge sur des exécutions répétées). Chaque tour respecte le contrat d'interface et laisse sa trace minimale.

Les tests correspondants sont dans `tests/atelier-03/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 03
atelier verifier 03
atelier verifier 03 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
