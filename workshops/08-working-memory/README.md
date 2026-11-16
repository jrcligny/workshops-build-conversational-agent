# Atelier 08 — La mémoire de travail

Chapitre 8 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

La compaction de l'atelier 07 résume l'historique ; elle peut donc perdre le dossier en cours. Vous allez donner à l'agent une mémoire de travail : un état de conversation explicite, tenu par le harnais hors de l'historique. Cet état (le client en cours, la commande en cours, les homonymes en attente de choix) est remis au modèle à chaque tour et traverse la compaction à l'identique. Le harnais le met à jour : il remplace le client ou la commande quand l'utilisateur change de dossier et oublie ce qui ne vaut plus. Une mémoire périmée est plus dangereuse qu'une mémoire absente.

## C'est réussi quand…

- Après une compaction, l'agent sait toujours quel client et quelle commande sont en cours : « celle-là » désigne encore la commande dont on parlait.
- L'état est réellement remis au modèle au début de chaque tour, pas seulement enregistré dans la trace.
- Pendant le choix entre deux homonymes, l'agent garde les deux candidats en mémoire ; une fois le choix fait, il s'y tient, même après une compaction.
- Quand l'utilisateur passe à un autre client, le client en cours est remplacé et la commande de l'ancien client est oubliée.

## Exemples

Données : la commande CMD-1042 appartient à Martin Durand (Nantes) et elle est livrée. Il existe deux clientes Léa Martin, l'une à Lille, l'autre à Lyon. Transports Morel est un client de Rennes.

| Conversation | Ce que l'agent doit faire |
| --- | --- |
| « Quel est le statut de la commande CMD-1042 de Martin Durand ? », puis une dizaine de tours « D'accord, continuez à suivre ce dossier. », puis « Et celle-là, où en est-elle ? » | Il comprend que « celle-là » est CMD-1042, la relit et répond qu'elle est livrée. |
| « Quelles sont les commandes de Léa Martin ? » | Il demande laquelle des deux et garde les deux candidates en mémoire. |
| « Celle de Lille, s'il vous plaît. », une dizaine de tours « Merci, restons sur ce dossier. », puis « Rappelez-moi le client en cours. » | Il répond Léa Martin de Lille, sans jamais parler de Lyon. |
| « Quel est le statut de la commande CMD-1042 de Martin Durand ? », puis « Passons maintenant à Transports Morel : combien a-t-il de commandes ? » | Transports Morel devient le client en cours, et CMD-1042 n'est plus la commande en cours. |

## À éviter

- Un état noté pour mémoire mais jamais montré au modèle : il ne sert à rien.
- Reconstruire l'état à partir du résumé de compaction : après quelques tours, « celle-là » n'est plus résolu de façon fiable.
- Remplacer le client sans oublier sa commande : c'est une mémoire périmée.
- Citer Lille et Lyon « pour être sûr » : le choix de l'utilisateur doit être respecté.

## Pistes

- Relisez votre compaction de l'atelier 07. L'état doit rester hors de ce qui est résumé et revenir à l'identique à chaque tour.
- Les homonymes viennent de la résolution de noms des ateliers 05 et 06.
- Décidez qui met l'état à jour et à quel moment : à partir des résultats d'outils, au changement de client, à la fin d'une tâche.
- La forme de l'état dans ce que voit le modèle est libre ; ce qui compte, c'est qu'il soit exact et à jour.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
