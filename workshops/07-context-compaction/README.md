# Atelier 07 — Contexte et compaction

Chapitre 7 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Le contexte est un budget : ce qui entre dans la fenêtre du modèle doit être borné et
déclaré. Un outil distingue ce qu'il affiche (quelques lignes) du total exact calculé par
la source. Pour un simple nombre, un mode de décompte fait compter la source plutôt que le
modèle. Le *harness* mesure la taille du contexte à chaque cycle. Quand la conversation
s'allonge, il la compacte : les anciennes réponses de l'agent sont remplacées par un
résumé, mais la demande initiale et tous les messages de l'utilisateur sont conservés à
l'identique, et l'utilisateur est prévenu.

## C'est réussi quand…

- sur une longue liste, l'agent montre un extrait, annonce que le résultat est partiel et
  donne le total exact ;
- sur une question de décompte, il obtient le nombre sans charger les lignes ;
- la taille du contexte est mesurée à chaque appel au modèle ;
- tant que la conversation reste courte, elle est rejouée telle quelle, sans compaction ;
- au-delà d'un seuil de messages, les anciennes réponses sont résumées, aucun message de
  l'utilisateur n'est perdu ni reformulé, et l'utilisateur est averti de la compaction.

## Exemples

| Question posée à l'agent | Ce que l'agent doit faire |
|---|---|
| « Quelles sont les commandes en retard de Transports Morel ? » | Il montre un extrait et annonce le total : « Voici les 20 premières sur 60 commandes en retard. » |
| « Combien de commandes en retard a Transports Morel ? Je veux seulement le nombre, pas les lignes. » | Il demande seulement le décompte à l'outil et répond « 60 commandes en retard. » |
| « Je traite le dossier de Martin Durand, commande CMD-1042, commandes livrées uniquement. », puis une dizaine de messages du type « Détail numéro 1 : je veux seulement les commandes livrées de CMD-1042. » | Une fois le seuil dépassé, il compacte la conversation en gardant mot pour mot la demande initiale et chaque message de l'utilisateur, et le signale. |

## À éviter

- Renvoyer les 60 lignes au modèle : le contexte n'est pas borné.
- Répondre « 20 commandes en retard » en comptant la page affichée.
- Résumer aussi les messages de l'utilisateur ou la demande initiale.
- Ajouter un résumé sans rien retirer de l'historique.

## Pistes

- Décidez combien de lignes un outil peut renvoyer, et faites-lui toujours annoncer le
  total et le fait que la liste est coupée.
- Pour un nombre, n'ayez pas besoin des lignes : demandez directement le compte à la source.
- La compaction porte sur ce que vous envoyez au modèle, pas sur la conversation que voit
  l'utilisateur.
- Demandez-vous ce qui peut être résumé sans risque (les réponses de l'agent) et ce qui ne
  doit jamais l'être (ce qu'a dit l'utilisateur).

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques)
est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le
[guide de démarrage](../../GETTING_STARTED.md).
