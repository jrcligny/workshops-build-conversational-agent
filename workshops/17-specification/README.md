# Atelier 17 — Spécifier un contrôle

Chapitre 18 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

Les contrôles du *harness* sont du code à écrire, à tester et à faire évoluer ; un *coding agent* peut en produire une part, à condition de ne pas lui abandonner les décisions. Le chapitre retient la **délégation contrôle par contrôle** : chaque contrôle devient une **spécification courte**, relue par une personne qui ne l'a pas rédigée, car « ce qui n'y figure pas sera décidé par le modèle ». L'implémentation s'accompagne d'essais, dont au moins un soumet au *harness* une **sortie du modèle volontairement fausse**. Le jeu de parcours de l'atelier 15 sert de critère d'acceptation : on peut l'exécuter, pas le modifier, et sa part réservée reste hors de portée. Utiliser un *coding agent* est facultatif.

## C'est réussi quand…

- Vous avez écrit, dans `my-agent/local-mode/specifications/`, la spécification d'un contrôle du *harness* avec ses cinq parties remplies : comportement, cas limites, résultats indésirables, vérification, hors périmètre.
- Vous avez écrit ses essais dans `my-agent/local-mode/controls/` : ils passent quand le contrôle est actif.
- Quand on désactive ce seul contrôle, au moins un essai échoue, parce qu'il fait produire au modèle une sortie fausse que seul le contrôle arrête.
- Les parcours officiels de l'atelier 15 restent intacts, et rien de ce que vous écrivez ne désigne leur part réservée.

## Exemples

Exemple de contrôle : « une référence citée sans avoir été consultée est signalée comme non vérifiée ».

- Un essai pose la question « Où en est la commande CMD-0000 ? » et force le modèle à répondre, sans consulter aucun outil, « La commande CMD-0000 est livrée. ».
- Contrôle actif : une mention signale CMD-0000 comme non vérifiée ; l'essai passe.
- Contrôle désactivé : aucune mention ; l'essai échoue, ce qui prouve que c'est bien le contrôle qui arrête l'erreur.

Pour ce contrôle, la spécification dirait par exemple : ce que voit l'utilisateur et à quel moment du tour le contrôle agit ; les cas limites (référence approchée comme CMD-1402, plusieurs références dans une phrase, référence citée par l'utilisateur) ; ce qui ne doit jamais arriver (référence inventée affichée sans mention, mention sur une référence consultée) ; comment on le vérifie (les essais, dont la sortie fausse, et les parcours de l'atelier 15) ; ce qu'elle ne couvre pas (réécrire la réponse du modèle, vérifier le sens du texte).

## À éviter

- Des essais qui passent avec et sans le contrôle : rien ne prouve alors que le contrôle sert à quelque chose.
- Des essais qui ne se lancent même pas : une erreur de chargement n'est pas un échec du contrôle.
- Une spécification avec des parties vides ou intitulées en anglais.
- Laisser un *coding agent* « corriger » un parcours officiel qui échoue : c'est à l'équipe de décider si le code ou le parcours doit changer.
- Mentionner l'emplacement de la part réservée des parcours, même en commentaire.

## Pistes

- Choisissez un contrôle dont la violation a une conséquence pour l'utilisateur ou l'application et qui s'observe sans lire le texte : une mention, un état, une trace, un journal.
- Prévoyez un moyen de désactiver ce seul contrôle, sans toucher au reste du *harness*.
- Réfléchissez à la façon d'imposer au modèle une sortie fausse, de manière reproductible.
- Relisez ligne à ligne ce qui touche à l'identité, aux droits, à la confirmation, à la soumission et au retrait des outils d'écriture, surtout si un *coding agent* l'a produit ; vérifiez qu'aucun test existant n'a été supprimé ni affaibli.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques) est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le [guide de démarrage](../../GETTING_STARTED.md).