# Contrôle : références non vérifiées

## Comportement
Quand la réponse finale du modèle cite une référence de commande (forme `CMD-…`) qu'aucun outil n'a consultée,
le harness ajoute, après la réponse, une `mention` « Référence non vérifiée : CMD-… » et trace la liste dans
`unverified_references`. Une référence est consultée si elle figure dans les arguments ou le résultat d'un appel
d'outil du tour, dans un appel ou un résultat d'outil du contexte stocké, ou dans le résumé de compaction. Le
contrôle agit à la fin du tour, sur le texte final ; le texte du modèle n'est pas modifié.

## Cas limites
Une référence seulement citée par l'utilisateur n'est pas consultée : la répéter sans l'avoir lue est signalé.
Plusieurs références dans une phrase donnent une seule mention qui les liste, sans doublon. Une référence
approchée (CMD-1402 quand l'outil a lu CMD-1042) est signalée, la comparaison est exacte. Une référence lue lors
d'un tour précédent, puis effacée par la compaction, reste consultée si le résumé la contient.

## Résultats indésirables
Une référence inventée affichée sans mention ; une mention sur une référence réellement consultée par un outil ;
une réponse réécrite ou bloquée par le contrôle ; un contrôle qui dépend du modèle (il est déterministe).

## Vérification
Les essais de `local-mode/controls/` font passer au contrôle une sortie volontairement fausse (« La commande
CMD-0000 est livrée. » sans appel d'outil) et vérifient la mention ; ils vérifient aussi qu'une référence lue par
un outil, du contexte ou du résumé n'est pas signalée. Avec `MY_AGENT_DISABLE_CONTROL=1`, le premier échoue.
Les parcours de l'atelier 15 vérifient que le reste du harness ne change pas.

## Hors périmètre
Vérifier le sens du texte (statut, montant) ; les autres identifiants (factures, fournisseurs, clients) ;
réécrire ou bloquer la réponse du modèle ; relancer un appel d'outil pour vérifier la référence.
