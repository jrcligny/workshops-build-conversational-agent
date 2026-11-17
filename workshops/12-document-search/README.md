# Atelier 12 — Répondre à partir de la documentation

Chapitre 13 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Les questions de procédure (« que faire quand une livraison arrive incomplète ? ») n'ont pas leur réponse dans les données de l'application, mais dans une documentation versionnée. Le chapitre ajoute donc un sixième outil de lecture : **rechercher dans la documentation**, avec l'identité de l'utilisateur.

Plusieurs règles encadrent cet outil. Le **filtrage** par organisation et par public se fait **avant** que le moindre passage n'entre dans le contexte. Seule la version **en vigueur** d'un document est consultable. Les **sources** affichées sont établies par le programme à partir des passages réellement trouvés, jamais rédigées par le modèle. Quand rien n'est trouvé, l'agent **s'abstient** et le dit. Enfin, l'agent distingue la **documentation** (ce qui devrait se passer) des **données** (ce qui s'est passé) : chacune a son outil.

## C'est réussi quand…

- L'agent répond aux questions de procédure à partir des passages trouvés, et l'interface affiche les sources utilisées avec leur titre et leur version.
- Les sources affichées ne citent que des documents réellement trouvés pendant le tour, jamais des données de l'application.
- Un utilisateur ne reçoit jamais un document qui ne lui est pas destiné.
- Une version retirée n'est jamais renvoyée ni citée.
- Sans passage pertinent, l'agent dit qu'il n'a rien trouvé, sans afficher de source.
- Une question mixte combine la recherche documentaire et une lecture de l'application.

## Exemples

| Qui | Question posée à l'agent | Ce que l'agent doit faire |
|---|---|---|
| Un chargé de clientèle | « Que dit la procédure quand une livraison arrive incomplète ? » | Il cherche dans la documentation et résume la procédure en vigueur (réclamation dans les cinq jours ouvrés, pas d'avoir promis avant consultation de la commande), avec sa source, version 2.1. |
| Un chargé de clientèle | « Que dit la documentation sur le voyage spatial des factures xyzzy-42 ? » | Il cherche, ne trouve rien de pertinent et le dit, sans source. |
| Un chargé de clientèle | « Donnez-moi la définition interne des statuts de facture, en particulier « réglée ». » | Il ne voit pas le document réservé à la comptabilité et dit ne pas disposer de cette définition. |
| Une comptable | La même question | Il répond à partir du document comptable sur les statuts de facture. |
| Un chargé de clientèle | « Quelle est la version en vigueur de la procédure des livraisons incomplètes ? » | Il répond « la version 2.1 », sans évoquer l'ancienne version. |
| Un chargé de clientèle | « Que dit la procédure pour une livraison incomplète, et quel est le statut de CMD-1042 ? » | Il cherche la procédure dans la documentation **et** relit la commande dans l'application : elle est livrée. Seule la procédure apparaît dans les sources. |

## À éviter

- Laisser le modèle écrire lui-même « Source : procédure v2.1 » dans sa réponse.
- Afficher en source un document que la recherche n'a pas renvoyé.
- Chercher sans l'identité de l'utilisateur, ou filtrer les passages après les avoir mis dans le contexte.
- Mettre les commandes dans la documentation, ou une commande dans les sources : une donnée n'est pas un document.
- Citer la version retirée d'une procédure.

## Pistes

- La recherche reçoit l'identité de l'utilisateur mise en place à l'atelier 10a ; c'est elle qui détermine ce qu'il a le droit de voir.
- La recherche renvoie presque toujours quelque chose : décidez comment l'agent constate qu'aucun passage n'est pertinent.
- Construisez les sources à partir des passages du tour, sans doublons.
- Une question mixte appelle deux outils : la recherche pour la procédure, la lecture de commande pour le statut.
- Restent libres : le nom de l'outil, ses paramètres et la formulation des réponses.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
