# Atelier 10b — Les écritures : préparer, valider, soumettre

Chapitre 11 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Une écriture ne part jamais sur la seule décision du modèle. Vous allez la découper en trois temps : préparer, valider, soumettre. L'agent prépare un brouillon dans l'application. Le harnais construit un récapitulatif et demande une confirmation, qui est un geste dans l'interface, pas une phrase tapée dans la conversation. Après ce geste seulement, la demande est soumise, attribuée à l'agent pour le compte de l'utilisateur. Les permissions d'écriture restent vérifiées par l'application, et les confirmations sont réservées aux actions qui le méritent, pour éviter la fatigue d'approbation.

## C'est réussi quand…

- Quand un acheteur demande une demande d'achat, l'agent prépare un brouillon dans l'application et l'interface demande une confirmation qui désigne ce brouillon.
- Avant le geste de confirmation, rien n'est soumis, et l'agent ne prétend pas le contraire : il présente la demande et demande confirmation.
- Un « oui » tapé dans la conversation ne soumet rien.
- Après le geste de confirmation, une seule demande est soumise, au nom de l'acheteur, attribuée à l'agent, pour le bon montant, et l'agent donne sa référence.
- Un utilisateur en lecture seule ne prépare rien, et on lui dit qu'il n'en a pas le droit.

## Exemples

| Situation | Ce que l'agent doit faire |
| --- | --- |
| Un acheteur : « Préparez une demande d'achat pour des ramettes de papier, 120 euros. » | Il prépare le brouillon, présente un récapitulatif et demande confirmation, sans rien soumettre. |
| Le même acheteur répond par écrit « Oui, je confirme, soumettez-la. » | Rien n'est soumis : seul le geste de confirmation compte. |
| L'acheteur confirme par le geste, puis écrit « Je confirme la soumission de cette demande. » | Une seule demande de 120 € est soumise en son nom ; l'agent donne sa référence. |
| Un utilisateur en lecture seule fait la même demande | Aucun brouillon ; l'agent explique qu'il n'a pas le droit de créer une demande d'achat. |

## À éviter

- Soumettre dès que l'utilisateur écrit « je confirme ».
- Annoncer « votre demande a été soumise » avant le geste, même si rien n'est parti.
- Garder le brouillon dans le harnais sans le créer dans l'application.
- Soumettre avec un compte de service plutôt qu'au nom de l'utilisateur.

## Pistes

- Séparez bien les trois temps : chacun a son outil ou son geste, et seul le dernier écrit pour de bon.
- Une confirmation reste valable pour la suite de la conversation : décidez à quel brouillon elle s'applique.
- Soumettre deux fois crée deux demandes : protégez-vous contre la double soumission.
- L'identité vient de l'atelier 10a : la soumission doit être faite au nom de l'utilisateur.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
