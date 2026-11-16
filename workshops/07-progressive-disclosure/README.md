# Atelier 07 — Découvrir le contexte progressivement

Chapitre 7 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Dans un agent, les consignes ne sont qu'une petite partie de ce que lit le modèle : le reste est assemblé à chaque cycle par le programme. Composer cette entrée, c'est de l'**ingénierie du contexte**, et le contexte se gère comme un budget : plus n'est pas mieux, et chaque élément doit justifier sa place par ce qu'il apporte à la décision suivante.

Cet atelier applique la **divulgation progressive** aux données : montrer d'abord un sommaire, et le détail seulement quand il devient utile. Aujourd'hui, votre outil « lister les commandes d'un client » (atelier 05) renvoie tout, sans limite et avec tout le détail. Vous allez le rendre raisonnable :

- une liste **résumée** (référence, date, état, date de livraison prévue) et **bornée** par une limite d'affichage basse ;
- le nombre de lignes renvoyées, le **total** et son statut : exact, ou seulement un minimum quand l'application cesse de compter à son plafond de récupération ;
- une **position** pour demander la portion suivante ;
- un **mode décompte**, qui donne le nombre sans les lignes ;
- le détail d'une commande obtenu avec l'outil de consultation de l'atelier 04.

L'agent annonce qu'un résultat est partiel et propose la suite ou une demande plus précise. Enfin, la taille du contexte est relevée à chaque cycle : c'est elle qui servira à régler la compaction de l'atelier 08.

## C'est réussi quand…

- Une liste longue tient en quelques lignes résumées, sans détail, avec le nombre renvoyé et le total exact.
- Au-delà du plafond de récupération, le total est annoncé comme un minimum (« au moins… »).
- « Montrez-moi les suivantes » donne de nouvelles lignes, sans répéter celles déjà reçues.
- Pour un simple décompte, l'agent obtient le nombre sans faire venir les lignes.
- Le détail d'une commande de la liste est lu avec l'outil de consultation.
- La réponse dit clairement que la liste est partielle.
- La taille du contexte est connue pour chaque cycle.

## Exemples

Sur le gros jeu de données, Transports Morel a 60 commandes en retard et plus de 200 commandes au total.

| Question posée à l'agent | Ce que l'agent doit faire |
|---|---|
| « Quelles sont les commandes en retard de Transports Morel ? » | Il montre les premières, en résumé, et annonce que ce n'est qu'une partie des 60, en proposant la suite. |
| « Montrez-moi les suivantes. » | Il montre la portion suivante, sans répéter les commandes déjà affichées. |
| « Quel est le montant de la première commande de cette liste ? » | Il consulte cette commande et donne son montant. |
| « Combien de commandes en retard a Transports Morel ? Je veux seulement le nombre, pas les lignes. » | Il répond 60, sans charger la liste. |
| « Listez toutes les commandes de Transports Morel. » | Il annonce qu'il y en a au moins 200, sans prétendre à un total exact. |

## À éviter

- Renvoyer toutes les lignes « pour être complet » : le contexte se remplit et la réponse se dégrade.
- Garder le détail complet dans chaque ligne de la liste.
- Compter soi-même les lignes affichées et annoncer ce nombre comme le total.
- Présenter comme exact un total arrêté au plafond.
- Tronquer en silence : le modèle ne peut pas expliquer une coupure qu'on ne lui signale pas.

## Pistes

- Partez de la décision à prendre au prochain cycle : quelles informations sont nécessaires maintenant, lesquelles pourraient l'être plus tard ?
- Distinguez la limite d'affichage, qui protège le contexte, du plafond de récupération, qui protège l'application.
- Relevez la taille du contexte avant chaque appel au modèle, et comparez-la avant et après vos changements.
- Vous retrouverez le même principe pour les outils à l'atelier 09 et pour les *skills* à l'atelier 14.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
