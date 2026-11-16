# Atelier 10c — Regroupements

## Critère de réussite

Une question de regroupement est calculée par l'outil d'interrogation, et son résultat est borné et déclaré. Aucun code produit par le modèle n'est exécuté. À une demande de médiane, l'agent répond qu'il ne peut pas la calculer et propose les agrégats disponibles.

Les tests correspondants sont dans `tests/atelier-10c/`. Ils restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par programme (état de l'application, traces, droits, événements d'interface) l'est en premier. Lorsqu'un critère porte sur la qualité d'une réponse, une grille de juge écrite s'applique ; l'appréciation de sens sera calibrée en phase B.

```bash
atelier commencer 10c
atelier verifier 10c
atelier verifier 10c --non-regression
```

Aucun corrigé n'est fourni. Vous travaillez dans `mon-agent/`.
