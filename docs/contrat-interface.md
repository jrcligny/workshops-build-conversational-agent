# Contrat d'interface agent ↔ tests

Ce contrat est stable pour tous les ateliers. Les capacités non encore utilisées (étapes, interruption, confirmation, sources, mentions) existent dans le protocole et restent inactives jusqu'à l'atelier qui les active.

## Point d'entrée de chat

| Élément | Contrat |
|---|---|
| Création | `POST /conversations` avec `utilisateur_id`, `role`, `organisation`, éventuellement `jeton_application`. Réponse : `{ "id": ... }`. |
| Tour | `POST /conversations/{id}/messages` avec `{ "texte": "..." }`. Réponse en flux SSE. |
| Événements (atelier 03) | `texte` (morceaux, champ `contenu`) puis `fin` (champ `ok`). Un événement `erreur` signale un échec de la coquille. |
| Multi-tour | Le même identifiant de conversation est réutilisé. Le *harness* doit rejouer l'historique dans l'entrée du modèle. |

Les tests utilisent le client en ligne de commande interne (`tests/communs/client_chat.py`), pas un navigateur.

## Traces

Une trace par tour, fichier JSONL dans le dossier configuré (`traces/` par défaut). Champs exigés dès l'atelier 03 :

- identifiants de conversation et de tour, horodatage ;
- entrée envoyée au modèle : *system prompt*, historique, nouveau message ;
- modèle : identifiant exposé par le proxy, *tokens*, durée, raison d'arrêt ;
- sortie : texte d'assistant ;
- outils : liste vide à l'atelier 03 ;
- aucun secret (clé Azure, jeton).

Si vous passez par le client `socle.modele.client.ClientModele`, les appels au modèle peuvent être complétés par vos propres écritures de trace (`socle.traces.tracer.ecrire`).

## Harness à implémenter

Dans `mon-agent/harness.py`, une classe `Harness` expose `tour(conversation_id, message, utilisateur, historique)` et cède des `Evenement`. La coquille livrée lève `NotImplementedError` : c'est voulu.
