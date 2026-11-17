# Atelier 06 — Boucle agentique

Chapitre 6 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Le *harness* devient une boucle agentique : observer, décider, agir, puis recommencer.
Chaque appel au modèle est un cycle ; un tour peut en compter plusieurs, et leur suite
forme une trajectoire. Les appels d'outils indépendants se groupent dans un même cycle ;
ceux qui dépendent d'un résultat précédent s'enchaînent sur des cycles successifs. Une
limite de cycles, large au départ puis resserrée, borne la boucle : quand elle est
atteinte, l'agent rend une réponse partielle et le dit. L'utilisateur peut aussi
interrompre le tour.

## C'est réussi quand…

- l'agent enchaîne seul plusieurs outils pour répondre à une question en plusieurs étapes,
  dans le bon ordre ;
- il lance ensemble, dans le même cycle, les appels qui ne dépendent pas l'un de l'autre ;
- il signale chaque étape à l'utilisateur pendant qu'il travaille ;
- à la limite de cycles, il s'arrête, le signale et présente sa réponse comme partielle,
  jamais comme complète ;
- si l'utilisateur a demandé l'interruption, il s'arrête proprement sans lancer d'outil ;
  sans interruption, la même demande s'exécute normalement.

## Exemples

| Question posée à l'agent | Ce que l'agent doit faire |
|---|---|
| « Trouvez Léa Martin de Lille et donnez-moi le statut de sa commande. » | Il cherche d'abord la cliente, puis, au cycle suivant, lit sa commande CMD-2010 et répond qu'elle est expédiée. |
| « Donnez-moi le statut de CMD-1042 et, en même temps, la liste des clients nommés Léa Martin. » | Il lance les deux recherches dans le même cycle. |
| « Faites une revue complète de toutes les commandes de Transports Morel, une par une, en vérifiant le détail de chacune, sans vous arrêter. » | Il atteint la limite, le signale et répond par exemple « Revue partielle : j'ai vérifié 8 commandes sur 30. » |
| « Trouvez Léa Martin de Lille, puis toutes ses commandes, puis leur détail. » après une demande d'interruption | Il s'arrête tout de suite, sans appeler d'outil, et le dit. |

## À éviter

- Annoncer « revue complète effectuée » alors que la limite a coupé la boucle.
- Enchaîner sur deux cycles deux appels qui auraient pu partir ensemble.
- Ignorer l'interruption et appeler quand même les outils.

## Pistes

- Pensez la boucle comme une suite de cycles : à chaque cycle, le modèle voit les résultats
  précédents et décide de la suite, ou répond.
- Choisissez une limite de cycles inférieure à ce qu'exige la revue de 30 commandes, sinon
  elle ne sera jamais atteinte.
- Vérifiez la demande d'interruption avant chaque cycle, avant tout outil.
- Une réponse partielle honnête vaut mieux qu'une réponse complète inventée : dites ce qui
  n'a pas été vérifié.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques)
est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le
[guide de démarrage](../../GETTING_STARTED.md).
