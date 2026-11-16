# Atelier 16 — De la consigne au contrôle

Chapitre 16 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Une consigne influence le modèle ; un contrôle s'applique quelle que soit sa sortie. Pour chaque règle de l'agent, posez-vous la question : que se passe-t-il si le modèle ne la suit pas ? L'équipe retient le **doublement selon la conséquence** : une règle dont la violation touche l'utilisateur ou les données garde sa consigne et reçoit en plus un contrôle du *harness*, qui rend l'écart visible lorsqu'il ne peut pas l'empêcher. Trois règles sont doublées : résultats partiels, ambiguïtés, sources. Enfin, les conversations simultanées sont isolées : la description de l'agent est partagée, mais la mémoire de travail, les *skills* chargés et l'identité appartiennent à chaque conversation.

## C'est réussi quand…

- Une réponse fondée sur une liste incomplète porte, sous la réponse, une mention construite par le *harness* : elle dit que la liste est partielle et donne le total.
- Quand un nom désigne plusieurs clients, aucun client n'est retenu tant que l'utilisateur n'a pas choisi.
- Une commande ou une facture citée sans avoir été trouvée dans l'application est cherchée, puis signalée comme non vérifiée dans une mention.
- Deux conversations ouvertes en même temps ne partagent ni état ni identité.

## Exemples

| Question posée à l'agent | Ce que l'agent doit faire |
|---|---|
| « Listez toutes les commandes en retard de Transports Morel. » (client avec beaucoup de commandes) | Il affiche les premières, puis une mention indique que la liste est partielle et donne le total (60 commandes en retard). |
| « Quelles sont les commandes de Léa Martin ? » | Il trouve deux Léa Martin (Lille et Lyon) et demande laquelle, sans en retenir aucune. |
| « Celle de Lille. » | Il retient Léa Martin de Lille comme client en cours. |
| « La facture FAC-9999 et la commande CMD-0000 sont-elles réglées ? » | Il cherche les deux références, ne les trouve pas, et une mention les cite comme non vérifiées. |
| Conversation A : « Quel est le statut de la commande CMD-1042 de Martin Durand ? » puis, dans une conversation B ouverte en parallèle : « Qui est le client en cours, et quelle commande est-ce que je suis ? » | B n'a ni client ni commande en cours et ne parle pas de Durand ; de retour dans A, « Et son client ? » obtient Durand. |

## À éviter

- Demander au modèle d'écrire lui-même « liste partielle » : c'est au *harness* de produire la mention.
- Une mention vague (« vérifiez vos références ») qui ne cite pas les références concernées.
- Affirmer que des références n'existent pas sans les avoir cherchées.
- Retenir la première Léa Martin trouvée comme client en cours.
- Ranger l'état de travail dans un endroit partagé entre conversations : la seconde conversation verrait la commande de la première.

## Pistes

- Relisez le tableau 16-3 du chapitre : il recense les règles et leur lieu. Ne doublez que celles dont la violation touche l'utilisateur.
- La mention des résultats partiels s'appuie sur ce que l'outil dit de son résultat (liste bornée, total), pas sur le texte du modèle.
- Une référence est « vérifiée » seulement si un outil l'a effectivement trouvée pendant le tour.
- La mémoire de travail de l'atelier 08 doit appartenir à chaque conversation ; vérifiez qu'aucune donnée d'une conversation ne vit dans un état partagé du *harness*.
- Un contrôle du *harness* s'applique quel que soit le texte produit par le modèle : ne comptez pas sur une instruction du *prompt système* pour le remplacer.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
