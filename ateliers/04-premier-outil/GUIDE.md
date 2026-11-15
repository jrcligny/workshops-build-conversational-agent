# Atelier 04 — Premier outil

## Critère de réussite

Votre agent consulte une commande au moyen de son premier outil. Une référence exacte est trouvée directement ; une référence approximative donne la commande la plus proche, et la réponse signale l'écart. Une commande exclue n'apparaît ni en consultation directe ni parmi les suggestions. Le résultat distingue réussite, absence de donnée et erreur, et l'agent fait au plus un appel d'outil par message.

Les tests correspondants sont dans `tests/atelier-04/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 04
atelier verifier 04
atelier verifier 04 --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
