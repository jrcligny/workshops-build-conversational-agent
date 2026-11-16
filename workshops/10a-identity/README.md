# Atelier 10a — L'identité et l'échange de jeton

Chapitre 10 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Le chapitre 10 applique le moindre privilège en quatre couches, dont aucune ne suffit seule. Cet atelier traite la première : au nom de qui l'outil agit-il ? Pas au nom d'un compte de service qui verrait tout, mais au nom de l'utilisateur, avec un jeton distinct émis pour l'application à partir du sien (un échange de jeton). Chaque maillon vérifie ce qu'il reçoit : le harnais, le serveur MCP, puis l'application. Aucun jeton n'entre dans le contexte du modèle. Sans identité valide, rien n'est lu.

## C'est réussi quand…

- Avec une identité valide, l'agent répond normalement, et chaque lecture faite dans l'application l'est au nom de cet utilisateur, avec un jeton obtenu par échange.
- La trace enregistre au nom de qui les outils ont agi.
- Sans jeton, avec un jeton mal formé ou signé par une autre clé, aucune donnée n'est lue : l'appel d'outil est tenté puis refusé, et la réponse ne donne pas l'information.
- Une utilisatrice d'une autre organisation ne voit pas les commandes de la première.
- Le serveur MCP de l'atelier 09 applique la même règle quand on l'appelle directement.

## Exemples

| Situation | Ce que l'agent doit faire |
| --- | --- |
| Camille, connectée, demande « Quel est le statut de la commande CMD-1042 ? » | Il lit la commande au nom de Camille et répond qu'elle est livrée. |
| Même question, mais sans identité valide (pas de jeton, jeton illisible ou contrefait) | L'outil est refusé ; l'agent ne donne pas le statut et peut expliquer que l'identité n'a pas pu être vérifiée. |
| Une utilisatrice de l'organisation B pose la même question | La lecture est faite à son nom et la commande, qui appartient à l'organisation A, n'est pas trouvée. |

## À éviter

- Fabriquer soi-même un jeton à partir du nom déclaré par l'utilisateur : c'est usurper son identité.
- Transmettre le jeton reçu tel quel à l'application, sans échange : elle le refuse.
- Ne rien tenter quand l'identité manque : le refus doit être visible comme résultat de l'outil.
- Utiliser un compte de service qui voit tout.

## Pistes

- Distinguez le jeton d'entrée (celui que l'interface remet au harnais) du jeton d'application (celui que l'application accepte).
- Chaque maillon doit vérifier le jeton, pas seulement le premier.
- La liste des outils peut rester consultable sans jeton ; seule la lecture des données l'exige.
- Attention à ne pas être plus strict que l'application sur les filtres acceptés.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
