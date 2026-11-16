# Atelier 08 — Compacter le contexte

Chapitre 8 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

La divulgation progressive de l'atelier 07 ralentit le remplissage du contexte, sans l'empêcher : une conversation qui dure finit par approcher la limite. Il faut alors **réduire** l'historique : tronquer, élaguer ou résumer. Vous allez mettre en place la **compaction par résumé** : au-delà d'un seuil, le programme fait rédiger un résumé des échanges anciens et le substitue à ces échanges. Les messages de l'utilisateur, qui portent sa demande initiale, ses décisions et les références qu'il a citées, sont conservés à l'identique ; seuls les réponses de l'agent et les résultats d'outils anciens sont résumés. L'utilisateur est prévenu qu'une partie ancienne de la conversation a été résumée.

Un résumé peut perdre ou déformer ce qui comptait. Ce qui doit survivre à la compaction sans passer par le résumé, c'est la **mémoire de travail** : un état de conversation explicite, tenu par le harnais hors de l'historique (le client en cours, la commande en cours, les homonymes en attente de choix). Cet état est remis au modèle à chaque tour et traverse la compaction à l'identique. Le harnais le met à jour : il remplace le client ou la commande quand l'utilisateur change de dossier et oublie ce qui ne vaut plus. Une mémoire périmée est plus dangereuse qu'une mémoire absente.

## C'est réussi quand…

- Tant que la conversation reste courte, l'historique est transmis tel quel, sans compaction.
- Au-delà du seuil, les anciennes réponses de l'agent sont remplacées par un résumé, que le modèle reçoit ensuite ; la demande initiale, les décisions de l'utilisateur et les références qu'il a citées restent mot pour mot.
- L'utilisateur est prévenu que le début de la conversation a été résumé.
- Après une compaction, l'agent sait toujours quel client et quelle commande sont en cours : « celle-là » désigne encore la commande dont on parlait.
- L'état est réellement remis au modèle au début de chaque tour, pas seulement enregistré dans la trace.
- Pendant le choix entre deux homonymes, l'agent garde les deux candidats ; une fois le choix fait, il s'y tient, même après une compaction.
- Quand l'utilisateur passe à un autre client, le client en cours est remplacé et la commande de l'ancien client est oubliée.

## Exemples

Données : la commande CMD-1042 appartient à Martin Durand (Nantes) et elle est livrée. Il existe deux clientes Léa Martin, l'une à Lille, l'autre à Lyon. Transports Morel est un client de Rennes.

| Conversation | Ce que l'agent doit faire |
| --- | --- |
| « Je traite le dossier de Martin Durand, commande CMD-1042, commandes livrées uniquement. », puis « Pouvez-vous simplement confirmer le client en cours ? » | Rien n'est résumé : la conversation est encore courte. |
| La même demande, puis une dizaine de précisions « Détail numéro 1 : je veux seulement les commandes livrées de CMD-1042. »… | À partir du seuil, les anciennes réponses sont résumées ; la demande initiale et chaque précision restent intactes, et l'utilisateur en est informé. |
| « Quel est le statut de la commande CMD-1042 de Martin Durand ? », une dizaine de tours « D'accord, continuez à suivre ce dossier. », puis « Et celle-là, où en est-elle ? » | Il comprend que « celle-là » est CMD-1042, la relit et répond qu'elle est livrée. |
| « Quelles sont les commandes de Léa Martin ? » | Il demande laquelle des deux et garde les deux candidates en mémoire. |
| « Celle de Lille, s'il vous plaît. », une dizaine de tours « Merci, restons sur ce dossier. », puis « Rappelez-moi le client en cours. » | Il répond Léa Martin de Lille, sans jamais parler de Lyon. |
| « Quel est le statut de la commande CMD-1042 de Martin Durand ? », puis « Passons maintenant à Transports Morel : combien a-t-il de commandes ? » | Transports Morel devient le client en cours, et CMD-1042 n'est plus la commande en cours. |

## À éviter

- Supprimer les messages les plus anciens : la demande initiale et les précisions de l'utilisateur disparaissent.
- Résumer aussi les messages de l'utilisateur : une référence ou une décision peut être déformée.
- Compacter sans le dire : l'utilisateur ignore que des informations ont changé ou disparu.
- Un état noté pour mémoire mais jamais montré au modèle : il ne sert à rien.
- Reconstruire l'état à partir du résumé : après quelques tours, « celle-là » n'est plus résolu de façon fiable.
- Remplacer le client sans oublier sa commande, ou citer Lille et Lyon « pour être sûr ».

## Pistes

- Décidez du seuil d'après les relevés de taille du contexte de l'atelier 07.
- Séparez nettement ce qui est résumé (réponses et résultats d'outils anciens) de ce qui est conservé à l'identique (messages de l'utilisateur, échanges récents, état).
- Chaque compaction coûte un appel au modèle : ne compactez pas à chaque tour.
- Décidez qui met l'état à jour et à quel moment : à partir des résultats d'outils, au changement de client, à la fin d'une tâche.
- La forme de l'état dans ce que voit le modèle est libre ; ce qui compte, c'est qu'il soit exact et à jour.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
