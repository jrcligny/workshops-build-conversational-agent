# Atelier 05 — Les outils de lecture et la boucle agentique

Chapitre 5 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Observez d'abord

En live, avec l'agent de l'atelier 04, demandez « Quelles commandes de Léa Martin sont en retard ? ».
Il ne sait consulter qu'une commande par sa référence : il demande une référence ou répond
de mémoire. La trace (`traces/turns.jsonl`) montre un seul appel au modèle, et aucun outil
capable de retrouver un client ou de lister ses commandes. (En simulé, le modèle répond
toujours par la même phrase prudente et n'appelle jamais d'outil.)

## Ce que vous allez construire

Un seul scénario porte l'atelier : retrouver les commandes en retard d'un client. Le travail
se fait en deux étapes, qui partagent ce scénario et ce dossier.

1. **Étape `outils`.** L'agent gagne deux outils de lecture : chercher un client par son nom
   et lister ses commandes, avec un filtre « en retard » appliqué par l'outil. La question du
   chapitre est : qui décide de l'étape suivante ? Quand le chemin est connu d'avance, le
   programme l'enferme dans un outil ; quand il ne l'est pas, le modèle décide.
2. **Étape `boucle`.** La même question demande désormais deux appels : retrouver le client,
   puis lister ses commandes. Le *harness* devient une boucle agentique : chaque appel au
   modèle est un cycle, et un tour peut en compter plusieurs. Les appels indépendants se
   groupent dans un même cycle. Une limite de cycles, large au départ, borne la boucle :
   quand elle est atteinte, l'agent rend une réponse partielle et le dit. L'utilisateur peut
   aussi interrompre le tour.

## C'est réussi quand…

Étape `outils` :

- face à deux clients qui portent le même nom, l'agent présente les deux et demande
  lequel est visé, sans choisir à la place de l'utilisateur ;
- pour compter les commandes en retard d'un client, il fait filtrer et compter par la
  source, puis donne le nombre exact ; le filtre « en retard » est demandé à l'outil, et non
  appliqué par le modèle sur une liste complète.

Étape `boucle` :

- l'agent retrouve le client, puis liste ses commandes en retard au cycle suivant ;
- il lance ensemble, dans le même cycle, les appels qui ne dépendent pas l'un de l'autre ;
- il signale chaque étape à l'utilisateur pendant qu'il travaille ;
- à la limite de cycles, il s'arrête, le signale et présente sa réponse comme partielle,
  jamais comme complète ;
- si l'utilisateur a demandé l'interruption, il s'arrête proprement sans lancer d'outil ;
  sans interruption, la même demande s'exécute normalement.

## Exemples

| Étape | Question posée à l'agent | Ce que l'agent doit faire |
|---|---|---|
| `outils` | « Quelles commandes de Léa Martin sont en retard ? » | Il trouve deux clientes, l'une à Lille, l'autre à Lyon, et demande laquelle est visée, sans lister les commandes de l'une d'elles. |
| `outils` | « Combien de commandes en retard a Transports Morel ? » | Il fait compter les retards par l'outil et donne le nombre exact (60 avec les données utilisées par les tests). |
| `boucle` | « Quelles commandes de Léa Martin, celle de Lille, sont en retard ? » | Il cherche d'abord la cliente, puis, au cycle suivant, liste ses commandes en retard. |
| `boucle` | « Quelles commandes sont en retard chez les deux Léa Martin, celle de Lille et celle de Lyon ? » | Après la recherche, il liste les commandes des deux clientes dans le même cycle. |
| `boucle` | « Faites une revue complète de toutes les commandes de Transports Morel, une par une… » | Il atteint la limite, le signale et répond par exemple « Revue partielle : j'ai vérifié 8 commandes sur 30. » |
| `boucle` | La même demande qu'au cycle chaîné, après une demande d'interruption | Il s'arrête tout de suite, sans appeler d'outil, et le dit. |

## À éviter

- Choisir la cliente de Lille et lister ses commandes : l'agent a tranché à la place de
  l'utilisateur.
- Lister toutes les commandes et laisser le modèle compter les retards : le nombre est fragile.
- Annoncer « revue complète effectuée » alors que la limite a coupé la boucle.
- Enchaîner sur deux cycles deux appels qui auraient pu partir ensemble.
- Ignorer l'interruption et appeler quand même les outils.

## Pistes

- Le nombre doit venir de la source : prenez le total qu'elle annonce, pas la longueur de
  la liste reçue.
- Un homonyme n'est pas une erreur : renvoyez les candidats et laissez le modèle poser la
  question.
- Pensez la boucle comme une suite de cycles : à chaque cycle, le modèle voit les résultats
  précédents et décide de la suite, ou répond.
- Choisissez une limite de cycles inférieure à ce qu'exige la revue de 30 commandes, sinon
  elle ne sera jamais atteinte. Vérifiez la demande d'interruption avant chaque cycle.
- À la limite, il faut quand même une réponse : refaites un dernier appel au modèle **sans
  outils** en lui demandant un bilan partiel, ou composez la réponse vous-même. Signalez la
  limite (`mention`) avant le texte.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques)
est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le
[guide de démarrage](../../GETTING_STARTED.md).
