# Atelier 05 — Deux outils de lecture

Chapitre 5 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

L'agent gagne deux outils de lecture : chercher un client par son nom et lister ses
commandes. La question du chapitre est : qui décide de l'étape suivante ? Quand le chemin
est connu d'avance, le programme enchaîne les étapes (un *workflow*). Quand il ne l'est
pas, le modèle décide (un agent). Entre les deux s'étend un continuum d'autonomie. Un
enchaînement stable, comme lister puis filtrer, gagne à être enfermé dans un outil.

## C'est réussi quand…

- face à deux clients qui portent le même nom, l'agent présente les deux et demande
  lequel est visé, sans choisir à la place de l'utilisateur ;
- pour compter les commandes en retard d'un client, il fait filtrer et compter par la
  source, puis donne le nombre exact ;
- le filtre « en retard » est demandé à l'outil, et non appliqué par le modèle sur une
  liste complète.

## Exemples

| Question posée à l'agent | Ce que l'agent doit faire |
|---|---|
| « Quelles sont les commandes de Léa Martin ? » | Il trouve deux clientes, l'une à Lille, l'autre à Lyon, et demande laquelle est visée, sans lister les commandes de l'une d'elles. |
| « Combien de commandes en retard a Transports Morel ? » | Il fait compter les retards par l'outil et donne le nombre exact (60 avec les données utilisées par les tests). |

## À éviter

- Choisir la cliente de Lille et lister ses commandes : l'agent a tranché à la place de
  l'utilisateur.
- Lister toutes les commandes et laisser le modèle compter les retards : le nombre est fragile.
- Donner « environ 60 » ou un nombre tiré d'une page partielle.

## Pistes

- Le nombre doit venir de la source : prenez le total qu'elle annonce, pas la longueur de
  la liste reçue.
- Le chemin « chercher le client, puis lister ses commandes » est connu d'avance : le
  programme peut l'enchaîner lui-même dans un même tour.
- Un homonyme n'est pas une erreur : renvoyez les candidats et laissez le modèle poser la
  question.
- Demandez-vous quelle part de décision vous laissez au modèle, et laquelle vous gardez
  dans le programme.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques)
est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le
[guide de démarrage](../../GETTING_STARTED.md).
