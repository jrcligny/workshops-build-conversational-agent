# Atelier 16 — Pannes et livraison

Chapitre 17 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Un agent dépend de services qui tombent, et la bonne réaction à une panne dépend du sort de la requête. Si le modèle principal est indisponible, le chapitre retient une **bascule unique** vers un modèle de repli, puis une fin de réponse propre si l'échec persiste. Si une soumission échoue sans qu'on sache si elle a été enregistrée, elle **ne se rejoue jamais** automatiquement : l'application ne reconnaît pas les répétitions, et l'utilisateur est invité à vérifier lui-même. Les lectures, elles, peuvent être réessayées. Enfin, consignes, catalogue de *skills*, définitions d'outils et index documentaire évoluent à leur rythme : chaque tour enregistre dans sa trace la **version** de chacun.

## C'est réussi quand…

- Quand le modèle principal est en panne, l'agent bascule une seule fois vers le modèle de repli, sans réessayer le principal en boucle.
- Il répond quand même, et dit que la réponse vient d'un modèle de secours.
- Une soumission dont l'issue est inconnue n'est tentée qu'une fois : l'agent dit qu'il ne sait pas si la demande a été enregistrée et invite à vérifier, sans prétendre qu'elle a réussi ni qu'elle a échoué.
- La trace de chaque tour indique la version des consignes, des outils, des *skills* et de l'index documentaire.

## Exemples

| Situation | Question posée à l'agent | Ce que l'agent doit faire |
|---|---|---|
| Modèle principal en panne | « Quel est le statut de la commande CMD-1042 de Martin Durand ? » | Il bascule une fois vers le modèle de repli et répond que CMD-1042 est livrée, en précisant que la réponse vient du modèle de secours. |
| Soumission à l'issue inconnue | Un acheteur demande « Préparez une demande d'achat pour des ramettes de papier, 120 euros. », confirme, puis écrit « Je confirme la soumission de cette demande. » | Il tente la soumission une seule fois, puis répond par exemple : « Je ne sais pas si votre demande a été enregistrée ; vérifiez dans l'application avant de recommencer. » |
| Tour ordinaire | « Quel est le statut de la commande CMD-1042 ? » | Il répond normalement ; la trace indique les versions en usage. |

## À éviter

- Réessayer le modèle principal avant de basculer.
- Rejouer la soumission « pour être sûr » après un échec dont l'issue est inconnue.
- Affirmer « votre demande a échoué » ou « a bien été soumise » alors qu'on n'en sait rien.
- Afficher une erreur générique sans réponse : le tour doit se terminer proprement et dire ce qui a été fait.
- Laisser une version vide ou oublier un composant.

## Pistes

- Le choix du modèle de repli relève de votre *harness*, pas du modèle.
- Distinguez le sort de la requête : un modèle indisponible n'a rien écrit ; une soumission sans réponse a peut-être écrit. Les lectures peuvent être réessayées, la soumission jamais.
- La soumission reprend le geste de confirmation de l'atelier 10b.
- Les versions se lisent là où vous les tenez : consignes, définitions d'outils, catalogue de *skills* (atelier 13), index documentaire (atelier 12).
- Un tour interrompu se termine par un signal explicite et un message qui dit ce qui a été fait et ce qui ne l'a pas été.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).