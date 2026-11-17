# Atelier 06 — Le serveur d'outils MCP et les regroupements

Chapitre 6 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Observez d'abord

Connectez-vous en comptable (nina-accountant) et demandez, avec l'agent de l'atelier 05,
« Quel est le montant total des factures en attente d'approbation ? ». Ses outils ne
connaissent que les clients et leurs commandes : il ne peut pas répondre, ou invente.
Lancez ensuite `uv run --project my-agent python my-agent/mcp_server.py` : le serveur MCP
de la coquille démarre, mais son catalogue est vide.

## Ce que vous allez construire

Le chapitre réunit deux décisions, que l'atelier traite en deux étapes.

1. **Étape `serveur`.** Les outils spécialisés se multiplient avec les questions. Vous les
   remplacez par un outil générique guidé par des exemples : interroger une source avec des
   filtres, et éventuellement un calcul (nombre, total, moyenne). Il est accompagné d'outils
   de découverte (lister les sources, décrire une source) et de la résolution de noms. Les
   valeurs codées sont traduites en libellés métier, et les messages d'erreur servent de
   guide : un filtre invalide renvoie les valeurs permises. Ces outils sont servis par un
   serveur MCP sans état, séparé du harnais (`my-agent/mcp_server.py`), et leurs noms suivent
   une convention par domaine.
2. **Étape `regroupements`.** Le contrôleur de gestion demande la répartition des montants
   facturés par fournisseur et par mois. Ce calcul ne se fait ni dans la tête du modèle, ni
   en lui faisant écrire du code : l'agent n'exécute pas de code produit par le modèle. Vous
   étendez l'outil d'interrogation aux regroupements, calculés par l'application. Ce qu'elle
   ne propose pas, comme la médiane, reste hors de portée : l'agent le dit et propose ce qui
   existe.

## C'est réussi quand…

Étape `serveur` :

- le serveur MCP publie un catalogue d'outils non vide, identique pour tous les clients ;
- les outils spécialisés du chapitre 5 (recherche de client, liste de commandes) ont disparu
  au profit d'un outil générique qui prend une source et des filtres ;
- pendant la conversation, chaque outil est appelé à travers le serveur MCP, qui interroge
  l'application par sa route générique ;
- une valeur codée invalide produit une erreur qui liste les valeurs permises ; l'agent
  corrige son filtre ou demande ce que l'utilisateur voulait dire ;
- la question simple d'une comptable aboutit par l'outil générique, et le total est calculé
  par l'application.

Étape `regroupements` :

- une question de regroupement (par fournisseur et par mois) est calculée par l'outil
  d'interrogation, et l'agent restitue chaque groupe avec son montant exact ;
- aucune ligne n'est rapatriée pour être regroupée ou additionnée par le modèle ;
- une demande de calcul « en Python » ne déclenche aucun outil d'exécution de code ;
- une demande de médiane est déclinée : l'agent dit qu'elle n'est pas proposée et oriente
  vers ce qui existe (nombre, total, moyenne).

## Exemples

| Étape | Question posée à l'agent | Ce que l'agent doit faire |
| --- | --- | --- |
| `serveur` | « Combien de commandes a Martin Durand ? » | Il passe par le serveur MCP, demande le nombre à l'application et répond une commande (CMD-1042). |
| `serveur` | « Listez les commandes dont le statut vaut DELIV. » | Son premier filtre est refusé avec la liste des statuts permis ; il corrige son filtre ou demande quel statut est visé. |
| `serveur` | En comptable : « Quel est le montant total des factures en attente d'approbation ? » | Il demande le total à l'application et répond 1280. |
| `regroupements` | En contrôleur de gestion : « Quelle est la répartition des montants facturés par fournisseur et par mois ? » | Il demande un total groupé par fournisseur et par mois, puis présente chaque fournisseur (Papeterie Atlantique, Bureau Plus, Transit Ouest) mois par mois. |
| `regroupements` | « Calculez vous-même, en Python, le montant moyen des commandes de Transports Morel. » | Il n'exécute aucun code ; il demande la moyenne à l'application et répond 506,04 €. |
| `regroupements` | « Quel est le montant médian des commandes de Transports Morel ? » | Il explique que la médiane n'est pas disponible et propose par exemple la moyenne. |

## À éviter

- Garder les anciens outils appelés directement par le harnais, sans passer par MCP.
- Relayer un filtre invalide tel quel : l'application renvoie zéro résultat au lieu d'une
  erreur utile.
- Lister les factures et laisser le modèle les regrouper ou les additionner.
- Offrir au modèle un outil qui exécute son code.
- Inventer une médiane par approximation.
- Un catalogue qui change selon le client ou l'ordre des connexions.

## Pistes

- Pensez « hôte, client, serveur » : le harnais est client du serveur MCP, qui est lui-même
  client de l'application.
- La vérification des valeurs codées revient au serveur MCP : l'application ne la fait pas
  pour vous.
- L'application déclare elle-même les calculs et les regroupements qu'elle sait faire
  (dont le mois, dérivé de la date) ; partez de là.
- Relayez l'identité de l'utilisateur de la conversation, pas une identité fixe : la
  question des factures demande un rôle de comptable ou de contrôleur.
- Les tests des ateliers 03 à 05 doivent continuer de passer : votre catalogue doit encore
  permettre de répondre à leurs questions.

## Pour aller plus loin

Le détail de ce que vérifient les tests est dans [contrat.md](contrat.md). Pour lancer
l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
