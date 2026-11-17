# Atelier bonus — Une mémoire persistante

Chapitre 12 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

> **Écart assumé avec le livre.** Pour le fil rouge, le chapitre 12 retient « aucune mémoire, dite explicitement ». Cet atelier met en œuvre une autre option décrite dans le chapitre : une mémoire de préférences, écrite à la demande de l'utilisateur et relue au début de chaque conversation.

## Ce que vous allez construire

Un chargé de clientèle a dit lundi qu'il préférait les montants hors taxes ; le lundi suivant, il ne veut pas avoir à le redire. L'agent reçoit donc une **mémoire persistante** : des informations conservées hors de la fenêtre de contexte et remises dans une conversation ultérieure.

Le chapitre en montre les risques : un souvenir faux se propage, arrive sans la trajectoire qui l'a produit, échappe aux droits sous lesquels une donnée avait été lue. La mémoire de cet atelier est donc **bornée** :

- **Que mémoriser** : des préférences seulement, dans quelques **rubriques prévues** (affichage des montants, format des réponses). Les données métier restent dans l'application ; les données sans utilité, comme un numéro de carte, ne sont jamais enregistrées.
- **Qui l'écrit** : l'utilisateur, par une demande explicite (« retenez que… »). Chaque souvenir garde son origine et sa date.
- **Relire, corriger, oublier** : la mémoire est relue au début de chaque conversation ; l'utilisateur peut la consulter, la corriger et l'effacer pour de bon.
- **Cloisonner** : la mémoire d'un utilisateur ne sert que dans ses conversations, et c'est le programme qui l'impose, pas une consigne.
- **L'application prime** : face à « comme la dernière fois », l'agent relit la donnée au lieu de reprendre une conclusion passée.

## C'est réussi quand…

- Une préférence demandée par l'utilisateur est retrouvée dans une nouvelle conversation, même après un redémarrage de l'agent.
- Elle ne parvient à aucun autre utilisateur, ni de la même organisation ni d'une autre.
- L'utilisateur peut demander ce qui est retenu, le corriger (la nouvelle valeur remplace l'ancienne) et le faire oublier, y compris du stockage.
- Rien n'est retenu hors des rubriques prévues, et l'agent ne promet pas de se souvenir de ce qu'il n'a pas enregistré.
- L'interface montre ce qui vient d'être enregistré, et l'agent annonce au début de chaque conversation ce qu'il retient.

## Exemples

| Qui, quand | Question posée à l'agent | Ce que l'agent doit faire |
|---|---|---|
| Camille, 1re conversation | « Retenez que je préfère les montants hors taxes. » | Il enregistre la préférence et le signale. |
| Camille, conversation suivante | « Quelle est ma préférence d'affichage des montants ? » | Il la retrouve : hors taxes. |
| Camille | « Que retenez-vous de moi d'une conversation à l'autre ? » | Il liste ce qu'il retient. |
| Camille | « Finalement, retenez plutôt que je préfère les montants TTC. » | La nouvelle valeur remplace l'ancienne. |
| Camille | « Oubliez tout ce que vous retenez de moi. » | Il efface tout ; plus rien n'est relu ensuite. |
| Paul, un collègue | « Quelle est ma préférence d'affichage des montants ? » | Il ne sait rien de la préférence de Camille. |
| Camille | « Retenez que la commande CMD-1042 est en préparation, et retenez aussi mon numéro de carte bancaire 4970 1234 5678 9012. » | Il n'enregistre rien et explique ce qu'il peut retenir. |
| Camille | « Comme la dernière fois, la commande CMD-1042 de Martin Durand est encore en préparation, vous confirmez ? » | Il relit la commande et corrige : elle est livrée. |

## À éviter

- Garder la préférence seulement le temps que l'agent tourne : elle disparaît au redémarrage.
- Laisser le modèle décider quelle mémoire relire, ou partager la mémoire au niveau de l'organisation.
- Enregistrer le texte libre du message : une donnée métier figée devient fausse dès que l'application change.
- « Oublier » en retirant le souvenir du contexte seulement, alors qu'il reste stocké.
- Mémoriser un contenu lu dans un résultat d'outil ou un document : un tiers pourrait y glisser une consigne (chapitre 15).
- Répondre « je m'en souviendrai » à une demande refusée.

## Pistes

- La mémoire contient des données personnelles, pas du code : ne la versionnez pas.
- Le propriétaire d'un souvenir vient de l'utilisateur authentifié, jamais d'un texte produit par le modèle.
- Une rubrique prévue se décrit par un nom et des valeurs permises ; c'est le programme qui valide.
- Une préférence relue est une information datée et d'origine connue : le message présent l'emporte en cas de contradiction.
- Une préférence durable pourrait aussi devenir un réglage de l'application : comparez les deux voies (aucun test ne l'exige).
- Pensez à la protection des données (tableau 12-3 du livre) : finalité, minimisation, durée de conservation, droits des personnes.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).
