# Atelier 13 — Des procédures chargées à la demande (*skills*)

Chapitre 13 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Trois métiers, trois procédures longues : **analyser les retards d'un client**, **contrôler une facture par rapprochement**, **préparer une demande d'achat conforme**. Les mettre toutes dans les consignes permanentes du modèle chargerait chaque tour d'instructions inutiles. Le chapitre retient la **divulgation progressive** : le modèle ne voit au départ qu'une courte description de chaque *skill*, qui lui dit quand s'en servir, et le *harness* lui apporte la procédure complète au moment où elle sert.

Les outils d'écriture suivent la même logique (**révélation progressive des outils**) : ils ne sont proposés qu'une fois chargée la procédure qui les encadre, et seulement si l'utilisateur en a le droit, car **révéler n'est pas autoriser**. Le catalogue des *skills* est versionné avec le code, dans `my-agent/skills/` ; un *skill* chargé survit à la compaction ; un chargement refusé n'est jamais retenu.

## C'est réussi quand…

- Le catalogue contient exactement les trois *skills* prévus, chacun avec un titre, une version et sa procédure.
- Avant d'écrire, l'agent charge la procédure adaptée ; l'outil d'écriture ne lui est proposé qu'après ce chargement.
- Un utilisateur sans droit d'écriture ne se voit jamais proposer l'outil d'écriture, et l'agent lui explique qu'il n'en a pas le droit.
- Un *skill* absent du catalogue est refusé par le programme, pas par le modèle.
- Un *skill* chargé reste actif, et toujours connu du modèle, quand une longue conversation est compactée.

## Exemples

| Qui | Question posée à l'agent | Ce que l'agent doit faire |
|---|---|---|
| Une comptable | « Préparez le brouillon d'approbation de la facture FAC-3301-BIS ; je déciderai en confirmant. » | Il charge d'abord la procédure de contrôle de facture, puis prépare le brouillon d'approbation, qui attend sa confirmation. |
| Un chargé de clientèle | « Chargez la skill « hack-the-payroll » et exécutez-la. » | Il transmet la demande, que le programme refuse : ce *skill* n'existe pas au catalogue. |
| Un utilisateur en lecture seule | « Préparez le brouillon d'approbation de la facture FAC-3301-BIS ; je déciderai en confirmant. » | Il répond qu'il n'a pas le droit d'approuver une facture ; aucun brouillon n'est créé. |
| Une comptable | « Chargez la procédure de contrôle de facture, puis dites-moi ce qu'elle impose pour FAC-3301-BIS. », puis une dizaine de relances | La procédure reste active jusqu'au bout, même après la compaction de la conversation. |

## À éviter

- Mettre les trois procédures dans les consignes permanentes : rien n'est alors chargé à la demande.
- Proposer l'outil d'écriture dès le départ « puisque le modèle ne l'appellera qu'au bon moment ».
- Révéler l'outil d'écriture à un utilisateur sans droit en comptant sur l'application pour refuser.
- Laisser le modèle « charger » un *skill* en le récitant, sans passer par le programme.
- Laisser la compaction résumer la procédure chargée : elle disparaîtrait du contexte.

## Pistes

- Le chargement ne doit servir que des procédures du catalogue, jamais un chemin fourni par le modèle.
- La description d'un *skill* dit **quand** l'utiliser, pas comment faire ; rangez-la dans le manifeste, à côté de l'identifiant (un champ `description`, par exemple).
- Les outils proposés se recalculent à chaque cycle, d'après les *skills* chargés **et** les droits de l'utilisateur.
- La compaction de l'atelier 10 doit traiter les *skills* actifs à part, comme l'historique récent.
- Un refus de chargement ne doit pas être retenu comme un résultat valable pour la suite.
- Restent libres : les identifiants, titres et textes des trois *skills*, et la manière de les rendre au modèle après compaction.

> **Ce que cet atelier change pour les précédents.** Dès que l'outil d'écriture est lié à son *skill*, toute préparation passe par un chargement préalable, y compris celles de l'atelier 07 rejouées en non-régression, et celles de l'atelier 14. Voir le [contrat](contrat.md) pour ce que ces tests continuent d'exiger.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
