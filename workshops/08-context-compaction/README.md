# Atelier 08 — Compacter le contexte

Chapitre 9 du livre ; l'état de la conversation que la compaction doit préserver est présenté au chapitre 7. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Votre agent rejoue tout le contexte à chaque tour : messages de l'utilisateur, appels d'outils et leurs résultats, réponses. La divulgation progressive de l'atelier 07 ralentit le remplissage, sans l'empêcher : une conversation qui dure finit par approcher la limite. Il faut alors **réduire** le contexte.

Plusieurs stratégies reconnues existent : la troncature (oublier les plus anciens), le **masquage des observations** (effacer les anciens résultats d'outils), le **résumé glissant** (*summary buffer* : garder les derniers tours, résumer ce qui précède), le **résumé structuré ancré** (un résumé à rubriques fixes, mis à jour plutôt que réécrit), ou le résumé hiérarchique. Vous allez en combiner trois, en deux étapes au-delà d'un seuil :

1. **Effacer les anciens résultats d'outils.** Tous les résultats d'outils déjà vus sont remplacés par un marqueur ; l'appel reste, pour que le modèle sache ce qui a été fait.
2. **Compacter.** Les derniers tours restent tels quels ; tout ce qui précède est remplacé par un **résumé à rubriques fixes**, rédigé par un appel au modèle séparé, avec son propre prompt système, que vous écrivez dans `my-agent/compaction_prompt.md`. Résumer n'est pas un acte neutre : ce prompt décide de ce qui survit. À la compaction suivante, le résumé est mis à jour à partir du résumé précédent et des tours qui sortent de la fenêtre.

L'utilisateur est prévenu qu'une partie ancienne de la conversation a été résumée.

Un résumé peut perdre ou déformer ce qui comptait. Ce qui doit survivre à coup sûr, c'est la **mémoire de travail** : un état de conversation explicite, tenu par le harnais hors de l'historique (le client en cours, la commande en cours, les homonymes en attente de choix). Cet état est remis au modèle à chaque tour et traverse la compaction à l'identique. Le harnais le met à jour : il remplace le client ou la commande quand l'utilisateur change de dossier et oublie ce qui ne vaut plus. Une mémoire périmée est plus dangereuse qu'une mémoire absente.

## C'est réussi quand…

- Tant que la conversation reste courte, tout le contexte est transmis tel quel.
- Au-delà du seuil, tous les anciens résultats d'outils sont remplacés par un marqueur, sans perdre les appels.
- Les derniers tours restent tels quels ; ce qui précède est remplacé par un résumé, rédigé par un appel au modèle séparé avec votre prompt de compaction.
- Le résumé suit cinq rubriques fixes : objectif de l'utilisateur, entités en cours, faits établis (avec l'outil qui les a lus), décisions et choix confirmés, questions en suspens. Un juge vérifie qu'il garde les faits lus par les outils.
- Le résumé glisse : la compaction suivante part du résumé précédent.
- Juste après la compaction, l'agent répond juste sur un fait qui n'existe plus que dans le résumé.
- L'utilisateur est prévenu que le début de la conversation a été résumé.
- Après une compaction, l'agent sait toujours quel client et quelle commande sont en cours : « celle-là » désigne encore la commande dont on parlait.
- L'état est réellement remis au modèle au début de chaque tour, pas seulement enregistré dans la trace.
- Pendant le choix entre deux homonymes, l'agent garde les deux candidats ; une fois le choix fait, il s'y tient, même après une compaction.
- Quand l'utilisateur passe à un autre client, le client en cours est remplacé et la commande de l'ancien client est oubliée.

## Exemples

Données : il existe deux clientes Léa Martin, l'une à Lille, l'autre à Lyon ; la commande CMD-2010 de Léa Martin (Lille) est expédiée, pour 450 €. CMD-1042 appartient à Martin Durand (Nantes). Transports Morel est un client de Rennes.

| Conversation | Ce que l'agent doit faire |
| --- | --- |
| Une réclamation de Léa Martin : l'agent cherche la cliente (deux homonymes), l'utilisateur répond « Celle du Nord. », l'agent lit sa commande CMD-2010 (450 €), puis quelques échanges sans nouveaux faits. | Sous le seuil : tout est rejoué tel quel. |
| La même conversation atteint le seuil, puis « Où en sommes-nous de ce dossier ? » | Les anciens résultats d'outils sont effacés, les tours anciens résumés sous les cinq rubriques : Léa Martin de Lille, CMD-2010 expédiée, 450 €, rappel souhaité en fin de semaine. L'utilisateur en est informé. |
| Au même moment : « Sans relire la commande, rappelez-moi son montant. » | Il répond 450 € à partir du résumé, sans relire la commande. |
| Au même moment : « Et celle-là, où en est-elle ? » | Il comprend que « celle-là » est CMD-2010 et répond qu'elle est expédiée. |
| « Quelles sont les commandes de Léa Martin ? », « Celle de Lille, s'il vous plaît. », d'autres tours, puis « Rappelez-moi le client en cours. » après une compaction | Il répond Léa Martin de Lille, sans jamais parler de Lyon. |
| « Quel est le statut de la commande CMD-1042 de Martin Durand ? », puis « Passons maintenant à Transports Morel : combien a-t-il de commandes ? » | Transports Morel devient le client en cours, et CMD-1042 n'est plus la commande en cours. |

## À éviter

- Supprimer les tours les plus anciens sans résumé : les faits lus par les outils disparaissent.
- Effacer un résultat d'outil en supprimant aussi son appel : le modèle reçoit des réponses sans origine.
- Résumer avec le prompt de l'agent, ou dans le même appel que la réponse : le résumé n'obéit à aucune consigne propre.
- Un résumé en prose libre, ou réécrit de zéro à chaque fois : ce qui comptait se perd au fil des compactions.
- Compacter sans le dire : l'utilisateur ignore que des informations ont changé ou disparu.
- Un état noté pour mémoire mais jamais montré au modèle : il ne sert à rien.
- Déduire l'état du résumé à chaque tour : il se reconstruit depuis les messages complets (par exemple quand une conversation est chargée), puis il est tenu à jour et traverse la compaction tel quel.
- Remplacer le client sans oublier sa commande, ou citer Lille et Lyon « pour être sûr ».

## Pistes

- Décidez du seuil et du nombre de tours gardés d'après les relevés de taille du contexte de l'atelier 07 ; les tests, eux, règlent leurs propres valeurs (`COMPACTION_MESSAGE_THRESHOLD`, `COMPACTION_KEEP_TURNS`).
- Rédigez le résumé à partir des tours sortants tels qu'ils étaient, résultats d'outils compris : c'est là que se trouvent les faits.
- Dans le prompt de compaction, imposez les rubriques et demandez de citer la source de chaque fait.
- Chaque compaction coûte un appel au modèle : ne compactez pas à chaque tour.
- Décidez qui met l'état à jour et à quel moment : à partir des résultats d'outils, au changement de client, à la fin d'une tâche.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubrique jugée) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
