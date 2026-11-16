# Atelier 04 — Premier outil

Chapitre 4 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

L'agent reçoit son premier outil : lire une commande à partir de sa référence. Le partage
des rôles est net : le modèle demande, le programme exécute. Avant d'exécuter, le
programme vérifie les arguments ; après, il renvoie un résultat de forme stable : trouvé,
proche, introuvable ou erreur. Retrouver une référence mal saisie est le travail de
l'outil, pas du modèle. Et les commandes exclues (supprimées ou rejetées) le restent,
y compris dans les suggestions.

## C'est réussi quand…

- pour une référence connue, l'agent consulte l'outil puis donne le statut qu'il a lu ;
- pour une référence proche d'une commande existante, il nomme les deux références et
  propose la commande proche sans présenter son statut comme la réponse ;
- pour une commande exclue, il répond qu'elle est introuvable, sans révéler qu'elle a existé ;
- une référence mal formée est rejetée par l'outil avant toute consultation de
  l'application métier ;
- chaque question donne lieu à un seul appel d'outil.

## Exemples

| Question posée à l'agent | Ce que l'agent doit faire |
|---|---|
| « Quel est le statut de la commande CMD-1042 de Martin Durand ? » | Il lit la commande avec l'outil, puis répond qu'elle est livrée. |
| « Quel est le statut de la commande CMD-1402 ? » | Il ne trouve pas CMD-1402 et demande : « Pensiez-vous à CMD-1042 ? » |
| « Quel est le statut de la commande CMD-0881 ? » | Il répond qu'il ne trouve pas cette commande, sans autre détail. |
| « Quel est le statut de la commande 1042;DROP ? » | Il demande une référence au format CMD-NNNN ; l'application métier n'est pas interrogée. |

## À éviter

- Répondre « CMD-1402 est livrée » : cette commande n'existe pas.
- Dire que CMD-0881 a été supprimée : l'exclusion doit rester invisible.
- Appeler l'outil deux fois pour une seule question.
- Laisser le modèle deviner la référence proche : c'est le rôle de l'outil.

## Pistes

- Décidez ce que l'outil renvoie dans chaque cas (trouvé, proche, introuvable, erreur) :
  une forme stable aide le modèle à formuler la bonne réponse.
- L'application métier ne sait pas chercher « à peu près » : c'est à votre outil de
  calculer les références candidates et de ne garder que celles qui existent.
- Vérifiez le format de la référence avant tout appel : une entrée invalide ne doit jamais
  atteindre l'application.
- Une commande exclue ne doit apparaître nulle part, même comme suggestion.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques)
est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le
[guide de démarrage](../../GETTING_STARTED.md).
