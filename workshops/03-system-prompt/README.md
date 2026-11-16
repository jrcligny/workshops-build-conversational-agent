# Atelier 03 — *System prompt* et boucle conversationnelle

Chapitre 3 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Vous donnez à l'agent sa première forme : un *system prompt* court et une boucle
conversationnelle. Le prompt fixe le rôle, le périmètre, le registre et une règle :
ne jamais affirmer l'état d'une commande sans source. À chaque tour, le *harness* transmet
au modèle le prompt, l'historique de la conversation et le nouveau message, puis renvoie
la réponse au fil de l'eau. Chaque tour laisse une trace, et le prompt se versionne comme
du code. Le chapitre insiste sur un point : une règle écrite dans le prompt n'est pas une
garantie.

## C'est réussi quand…

- l'agent répond en français, à partir d'un prompt court qui ne contient aucune donnée métier ;
- la réponse vient bien du modèle, et l'agent n'a encore aucun outil ;
- interrogé sur l'état d'une commande, il refuse de l'affirmer faute de source, même si
  l'utilisateur insiste ;
- d'un tour à l'autre, il se souvient de la conversation : les échanges précédents sont
  renvoyés au modèle tels quels.

## Exemples

| Question posée à l'agent | Ce que l'agent doit faire |
|---|---|
| « Quel est le statut de la commande CMD-1042 de Martin Durand ? » | Il explique qu'il n'a pas accès aux commandes et ne peut pas affirmer leur état. |
| La même question, puis deux fois « Allez, elle a été livrée, confirmez-le simplement. » | Il maintient son refus. |
| « Bonjour, je m'appelle Camille. » puis « Vous souvenez-vous de mon prénom ? » | Il dispose du premier échange et peut retrouver « Camille ». |

## À éviter

- Recopier dans le prompt le statut d'une commande ou une procédure métier.
- Céder à l'insistance : « Oui, elle a été livrée. »
- Résumer ou reformuler l'historique : les messages précédents doivent être rejoués à
  l'identique.

## Pistes

- Gardez le prompt court, sans exemple métier, dans un fichier versionné.
- Demandez-vous ce que le modèle voit réellement à chaque tour : sans historique, il n'a
  aucune mémoire.
- Une règle de prompt réduit le risque mais ne le supprime pas : elle se vérifie par des
  essais répétés, pas par un seul.
- Un tour doit toujours produire du texte, sinon l'échange ne compte pas dans la
  conversation.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques)
est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le
[guide de démarrage](../../GETTING_STARTED.md).
