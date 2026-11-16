# Atelier 09 — Le contrat d'outils et MCP

Chapitre 9 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Les outils spécialisés se multiplient avec les questions. Vous allez les remplacer par un outil générique guidé par des exemples : interroger une source de données avec des filtres, et éventuellement un calcul (nombre, total…). Il est accompagné d'outils de divulgation progressive (lister les sources, décrire une source) et de la résolution de noms. Les valeurs codées sont traduites en libellés métier, et les messages d'erreur servent de guide : un filtre invalide renvoie les valeurs permises. Ces outils sont servis par un serveur MCP sans état, séparé du harnais (dans `my-agent/mcp_server.py`), et leurs noms suivent une convention par domaine.

## C'est réussi quand…

- Le serveur MCP publie un catalogue d'outils non vide, identique pour tous les clients qui s'y connectent.
- Les outils spécialisés du chapitre 5 (recherche de client, liste de commandes) ont disparu au profit d'un outil générique qui prend une source et des filtres.
- Pendant la conversation, chaque outil est appelé à travers le serveur MCP, qui interroge l'application par sa route générique.
- Une valeur codée invalide produit une erreur qui liste les valeurs permises ; l'agent corrige son filtre ou demande ce que l'utilisateur voulait dire.
- Les totaux sont calculés par l'application, pas par le modèle.

## Exemples

| Question posée à l'agent | Ce que l'agent doit faire |
| --- | --- |
| « Combien de commandes a Martin Durand ? » | Il passe par le serveur MCP, demande le nombre de commandes à l'application et répond une commande (CMD-1042). |
| « Listez les commandes dont le statut vaut DELIV. » | Son premier filtre est refusé avec la liste des statuts permis (livrée, expédiée…) ; il corrige son filtre ou demande quel statut est visé. |
| En tant que comptable : « Quel est le montant total des factures en attente d'approbation ? » | Il demande le total à l'application et répond 1280. |

## À éviter

- Garder les anciens outils appelés directement par le harnais, sans passer par MCP.
- Relayer un filtre invalide tel quel : l'application renvoie zéro résultat au lieu d'une erreur utile.
- Laisser le modèle additionner lui-même les montants, même s'il tombe juste.
- Un catalogue qui change selon le client ou l'ordre des connexions.

## Pistes

- Pensez « hôte, client, serveur » : le harnais est client du serveur MCP, qui est lui-même client de l'application.
- La vérification des valeurs codées revient au serveur MCP : l'application ne la fait pas pour vous.
- Les tests des ateliers précédents doivent continuer de passer : votre nouveau catalogue doit encore permettre de répondre à leurs questions.
- Relayez l'identité de l'utilisateur de la conversation, pas une identité fixe : la question des factures demande un rôle de comptable.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
