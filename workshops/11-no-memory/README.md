# Atelier 11 — Ne rien garder, et le dire

Chapitre 11 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Observez d'abord

Dites à votre agent « Retenez que je préfère les montants hors taxes. », puis ouvrez une nouvelle conversation et demandez « Quelle est ma préférence d'affichage des montants ? ». Que répond-il la première fois : promet-il de s'en souvenir ? Que sait-il la seconde ? Et qu'est-ce qui, dans l'interface, a prévenu l'utilisateur ?

## Ce que vous allez construire

Les utilisateurs demandent à l'agent de « se souvenir ». Le chapitre pèse les options (mémoire de préférences, mémoire écrite par le modèle, mémoire d'épisodes) et retient, pour le fil rouge, **aucune mémoire entre conversations, dite explicitement** : les préférences formulées sont peu nombreuses et relèvent de réglages ; les conclusions passées vieillissent, alors que l'application est à jour.

Ne rien garder ne suffit pas : l'agent ne doit pas laisser croire le contraire. Vous allez :

- faire **annoncer par l'interface**, à l'ouverture de chaque conversation, que rien n'est gardé d'une conversation à l'autre — une annonce qui ne dépend pas du modèle ;
- demander dans les consignes que l'agent **ne promette jamais de se souvenir** : à « retenez que… », il répond qu'il en tiendra compte jusqu'à la fin de la conversation ;
- faire **relire l'application** quand l'utilisateur évoque un travail antérieur, au lieu de supposer une conclusion passée ;
- **signaler à l'éditeur** les préférences durables, comme candidates à devenir des réglages : un signal dans la trace, anonyme, qui n'est jamais rechargé dans une conversation. C'est la différence entre *observer un besoin* et *mémoriser*.

## C'est réussi quand…

- La première réponse de chaque conversation est précédée d'une annonce de l'interface : rien n'est gardé d'une conversation à l'autre.
- À « retenez que… », l'agent applique la préférence jusqu'à la fin de la conversation, sans promettre de s'en souvenir.
- Dans la conversation suivante, rien de la précédente n'arrive au modèle.
- La préférence durable est signalée dans la trace, sans nom d'utilisateur ni donnée métier, et n'est jamais remise dans une conversation.
- « Comme la dernière fois… » conduit l'agent à relire la commande et à corriger l'utilisateur si elle a changé.

## Exemples

| Question posée à l'agent | Ce que l'agent doit faire |
|---|---|
| « Bonjour » (début de conversation) | L'interface annonce que rien n'est gardé d'une conversation à l'autre. |
| « Retenez que je préfère les montants hors taxes. » | Il en tient compte jusqu'à la fin de la conversation et dit qu'il ne le gardera pas au-delà. |
| « Quelle est ma préférence d'affichage des montants ? » (nouvelle conversation) | Il ne la connaît pas, et le dit. |
| « Comme la dernière fois, la commande CMD-1042 de Martin Durand est encore en préparation, vous confirmez ? » | Il relit la commande : elle est livrée. |

## À éviter

- « C'est noté, je m'en souviendrai » : une promesse que le programme ne tient pas.
- Confier l'annonce au modèle : elle doit être émise par l'interface, à chaque ouverture.
- Remettre les signalements dans les consignes ou l'historique : ils deviendraient une mémoire.
- Signaler autre chose qu'une rubrique prévue : un fournisseur, une commande ou un IBAN n'ont rien à faire dans un signalement.

## Pistes

- L'annonce est un événement de l'interface au premier tour de la conversation, comme la mention de l'atelier 03.
- Le signalement est un champ de la trace du tour : l'éditeur les agrège en lisant `traces/turns.jsonl`.
- Pour reconnaître une préférence durable, quel que soit le phrasé, laissez le modèle la signaler par un outil local du harnais aux valeurs énumérées (par exemple `report_preference`, voir [contrat.md](contrat.md)) plutôt que par une règle sur le texte.
- Si vous avez fait l'atelier bonus (mémoire de préférences), ses tests et ceux de cet atelier s'excluent : ce sont deux choix opposés du chapitre.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
