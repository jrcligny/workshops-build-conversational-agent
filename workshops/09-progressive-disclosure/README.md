# Atelier 09 — Borner l'outil d'interrogation

Chapitre 9 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Observez d'abord

Lancez votre agent sur le jeu `volume` (voir [contrat.md](contrat.md)) et demandez « Quelles sont les commandes en retard de Transports Morel ? ». Ouvrez la dernière ligne de `traces/turns.jsonl` : combien de lignes l'outil d'interrogation a-t-il renvoyées au modèle, avec quels champs ? Que dit la réponse du total ? Notez `model.calls[].context_size` si vous le relevez déjà : c'est la mesure que cet atelier va faire baisser.

## Ce que vous allez construire

Dans un agent, les consignes ne sont qu'une petite partie de ce que lit le modèle : le reste est assemblé à chaque cycle par le programme. Composer cette entrée, c'est de l'**ingénierie du contexte**, et le contexte se gère comme un budget : plus n'est pas mieux, et chaque élément doit justifier sa place par ce qu'il apporte à la décision suivante.

Cet atelier applique la **divulgation progressive** aux données, sur l'outil d'interrogation générique de l'atelier 06 (`source`, `filters`, `aggregate`, `group_by`). Aujourd'hui, il peut faire venir des centaines de lignes complètes. Vous allez le rendre raisonnable :

- une liste **résumée** (référence, date, état, date de livraison prévue) et **bornée** par une limite d'affichage basse ;
- le nombre de lignes renvoyées, le **total** et son statut : exact, ou seulement un minimum quand l'application cesse de compter à son plafond de récupération ;
- une **position** pour demander la portion suivante ;
- un **décompte**, qui donne le nombre sans les lignes (l'agrégat `count` de l'atelier 06) ;
- les mêmes bornes pour les **regroupements** : beaucoup de groupes, c'est aussi beaucoup de lignes ;
- le détail d'une commande obtenu avec l'outil de consultation de l'atelier 04.

L'agent annonce qu'un résultat est partiel et propose la suite ou une demande plus précise. Enfin, la taille du contexte est relevée à chaque cycle : c'est elle qui servira à régler la compaction de l'atelier 10.

## C'est réussi quand…

- Une liste longue tient en quelques lignes résumées, sans détail, avec le nombre renvoyé et le total exact.
- Au-delà du plafond de récupération, le total est annoncé comme un minimum (« au moins… »).
- « Montrez-moi les suivantes » donne de nouvelles lignes, sans répéter celles déjà reçues.
- Pour un simple décompte, l'agent obtient le nombre sans faire venir les lignes.
- Le détail d'une commande de la liste est relu dans l'application avec l'outil de consultation, au moment où on le demande.
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
- Recréer un outil « lister les commandes » à côté de l'outil d'interrogation : c'est lui qu'on borne, en gardant ses paramètres (`source`, `filters`, `aggregate`, `group_by`), que les tests lisent.

## Pistes

- Partez de la décision à prendre au prochain cycle : quelles informations sont nécessaires maintenant, lesquelles pourraient l'être plus tard ?
- Distinguez la limite d'affichage, qui protège le contexte, du plafond de récupération, qui protège l'application.
- Les bornes se posent dans le serveur d'outils : c'est lui qui connaît la forme des résultats.
- Relevez la taille du contexte avant chaque appel au modèle, et comparez-la avant et après vos changements.
- Vous retrouverez le même principe pour les *skills* à l'atelier 13.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
