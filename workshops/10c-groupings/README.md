# Atelier 10c — Les regroupements calculés par l'application

Chapitre 10 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Un total, une moyenne ou un décompte sur des centaines de lignes ne se calcule pas dans la tête du modèle. Il ne se calcule pas non plus en lui faisant écrire du code : l'agent n'exécute pas de code produit par le modèle. Vous allez confier ces calculs à l'application, à travers l'outil générique de l'atelier 09 : des agrégats, éventuellement par groupe, dont le résultat est borné et déclaré. Ce que l'application ne propose pas, comme la médiane, reste hors de portée : l'agent le dit et propose ce qui existe.

## C'est réussi quand…

- Sur un gros volume de commandes (420 pour Transports Morel), le montant total puis le montant moyen sont calculés par l'application, et l'agent donne la valeur exacte.
- Aucune longue liste de lignes n'est rapatriée pour être additionnée par le modèle.
- Une demande de calcul « en Python » ne déclenche aucun outil d'exécution de code : l'agent passe quand même par l'application.
- Une demande de médiane est déclinée : l'agent dit que la médiane n'est pas proposée et oriente vers ce qui existe (nombre, total, moyenne).

## Exemples

Pour Transports Morel, sur le gros jeu de données : 420 commandes, total 212 538,50 €, moyenne 506,04 €.

| Question posée à l'agent | Ce que l'agent doit faire |
| --- | --- |
| « Quel est le montant total des commandes de Transports Morel ? » | Il demande le total à l'application et répond 212 538,50 €. |
| « Calculez vous-même, en Python, le montant moyen des commandes de Transports Morel. » | Il n'exécute aucun code ; il demande la moyenne à l'application et répond 506,04 €. |
| « Quel est le montant médian des commandes de Transports Morel ? » | Il explique que la médiane n'est pas disponible et propose par exemple la moyenne. |

Pour aller plus loin, un regroupement (par exemple le total par statut de commande) renvoie une ligne par groupe ; aucun test ne pose encore de question groupée.

## À éviter

- Lister toutes les commandes et laisser le modèle les additionner.
- Offrir au modèle un outil qui exécute son code.
- Arrondir la réponse (« environ 212 500 € ») au lieu de donner la valeur exacte.
- Inventer une médiane par approximation (« la médiane s'élève à 480 € »).

## Pistes

- L'application déclare elle-même les calculs qu'elle sait faire ; partez de là.
- Le refus de la médiane vient de l'application, avec la liste des calculs disponibles : transmettez-la au modèle.
- Un résultat sans calcul est déjà borné par l'application ; gardez cette information jusqu'au modèle pour qu'il sache quand une liste est tronquée.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
