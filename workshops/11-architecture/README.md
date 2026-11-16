# Atelier 11 — Un agent unique : requêtes sur la trace

Chapitre 11 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Le même agent sert désormais trois métiers. Le chapitre compare trois architectures : des agents spécialisés avec un routage, un agent principal qui délègue à des sous-agents, ou un **agent unique, sans délégation**. L'équipe garde l'agent unique : les demandes à cheval sur plusieurs métiers tiennent dans un seul contexte, alors qu'un routage buterait sur ces demandes et que des sous-agents ajouteraient missions, comptes rendus et cycles.

Une décision d'architecture s'accompagne de **critères de réexamen** mesurables. Le chapitre en retient deux : des tours saturés par les **lectures intermédiaires** (les résultats d'outils qui remplissent le contexte), et l'apparition, dans un même tour, de **domaines aux droits incompatibles**. Votre travail : exprimer ces deux critères sous forme de requêtes sur la trace, dans un module `my-agent/trace_queries.py`. Le code de l'agent, lui, ne change pas.

## C'est réussi quand…

- L'agent reste unique : ni sous-agent ni routage.
- Une première requête donne, tour par tour, la part du contexte occupée par les lectures intermédiaires (un nombre entre 0 et 1, nul pour un tour sans outil).
- Une seconde requête signale les seuls tours qui ont réuni des domaines dont les droits de lecture diffèrent.
- Les deux requêtes fonctionnent aussi bien sur les traces d'exemple fournies que sur les traces écrites par votre agent.

## Exemples

| Situation | Résultat attendu |
|---|---|
| Un tour où les résultats d'outils occupent 2 500 des 4 000 unités du contexte | Part des lectures intermédiaires : 0,625. |
| Un tour sans aucun appel d'outil | Part nulle. |
| Un tour qui lit des commandes et des factures (les factures ne sont lisibles que par la comptabilité) | Le tour est signalé, avec ces deux domaines. |
| Un tour qui lit des clients et des commandes (mêmes droits de lecture) | Le tour n'est pas signalé. |
| Votre agent répond à « Quel est le statut de la commande CMD-1042 ? » | Sa trace donne une part strictement positive (il a appelé un outil) et aucun domaine incompatible. |

## À éviter

- Renvoyer des valeurs fixes plutôt que les calculer pour chaque tour.
- Signaler tout tour qui touche plusieurs domaines : seuls comptent des domaines aux droits **différents**.
- Comparer les domaines au rôle de l'utilisateur plutôt qu'entre eux.
- Écrire des requêtes qui ne marchent que sur les traces d'exemple : sur les traces de votre agent, la part vaudrait zéro.
- Ajouter un sous-agent ou un routage « pour essayer » : l'atelier fait le choix inverse.

## Pistes

- La part se lit « lectures intermédiaires / taille totale du contexte » du tour.
- Votre trace relève déjà la taille du contexte depuis l'atelier 07, et les résultats d'outils sont les lectures intermédiaires : c'est de là que vos requêtes doivent partir.
- Le domaine d'un appel se déduit de ce que l'outil lit, par exemple la source interrogée par l'outil générique de l'atelier 09.
- Les requêtes doivent pouvoir s'exécuter seules, hors du serveur : ne les faites dépendre d'aucun état de l'agent.
- Restent libres : l'unité de mesure du contexte (caractères ou *tokens*) et la manière d'enregistrer le domaine de chaque appel.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
