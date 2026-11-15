# Contrat d'interface agent ↔ tests

Ce contrat est stable pour tous les ateliers. Les capacités non encore utilisées (étapes, interruption, confirmation, sources, mentions, pièces jointes) existent dans le protocole et restent inactives jusqu'à l'atelier qui les active.

## Point d'entrée de chat

| Élément | Contrat |
|---|---|
| Création | `POST /conversations` avec `utilisateur_id`, `role`, `organisation`, éventuellement `jeton_application`. Réponse : `{ "id": ... }`. |
| Tour | `POST /conversations/{id}/messages` avec `{ "texte": "..." }`. Réponse en flux SSE. |
| Événements (atelier 03) | `texte` (morceaux, champ `contenu`) puis `fin` (champ `ok`). Un événement `erreur` signale un échec de la coquille. |
| Multi-tour | Le même identifiant de conversation est réutilisé. Le *harness* doit rejouer l'historique dans l'entrée du modèle. |

Les tests utilisent le client en ligne de commande interne (`tests/communs/client_chat.py`), pas un navigateur.

## Pièces jointes (réservé à l'atelier 15)

Le contrat prévoit déjà le point d'entrée, sans fichier fourni dans la coquille :

| Élément | Contrat |
|---|---|
| Liste | `GET /pieces-jointes` renvoie `{ "pieces_jointes": [...] }` à partir de la zone `services/pieces_jointes/`. Dans la coquille, la liste est vide. |
| Tour | Le corps de `POST /conversations/{id}/messages` accepte un champ optionnel `pieces_jointes` (liste d'identifiants). Il est transmis au *harness* (`tour(..., pieces_jointes=...)`). |
| Événement réservé | `piece_jointe` pourra signaler une lecture de document joint. |

Aucun devis d'essai n'est déposé dans la coquille. Vous alimenterez la zone à l'atelier 15.

## Serveur MCP (coquille vide, à brancher à l'atelier 09)

La coquille inclut `mon-agent/serveur_mcp.py` : un serveur MCP qui démarre et répond au handshake, écrit avec le SDK Python officiel `mcp`. Il n'expose **aucun outil métier**. Transport prévu : HTTP en flux (`streamable-http`), mode sans état, point d'entrée `/mcp` (port 8004 par défaut).

```bash
uv run python mon-agent/serveur_mcp.py
```

À l'atelier 09, vous y migrerez les outils et les brancherez sur l'API métier. Les tests de l'atelier 09 restent rouges tant que ce branchement n'est pas fait.

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

Dans `mon-agent/harness.py`, une classe `Harness` expose `tour(conversation_id, message, utilisateur, historique, pieces_jointes=None)` et cède des `Evenement`. La coquille livrée lève `NotImplementedError` : c'est voulu.

## Autres emplacements de la coquille

| Emplacement | Rôle | État dans la coquille |
|---|---|---|
| `services/confinement/` | Interface et politique du confinement (atelier 10d) | Présent, politique inactive, liste d'autorisation vide |
| `services/catalogue/` | Catalogue versionné de *skills* (atelier 14) | Manifeste valide, zéro *skill* |
| `services/pieces_jointes/` | Zone en lecture seule des documents joints (atelier 15) | Vide |
| `mon-agent/mode-local/` | Accueil du mode de développement (atelier 19, *coding agent* facultatif) | Structure vide (`specifications/`, `controles/`) |


## Événements et gestes réservés (ateliers 06, 07, 10b)

| Élément | Contrat |
|---|---|
| Étape | Événement SSE `etape` pendant un tour à plusieurs cycles (atelier 06). |
| Interruption | `POST /conversations/{id}/interruption`, ou champ `interrompre` du message. Le *harness* reçoit `interruption_demandee=True` et arrête le tour sans nouvel appel (événement `interruption`). |
| Compaction | Événement SSE `compaction` (ou `mention` qui l'annonce) lorsque l'historique a été compacté (atelier 07). La trace décrit le moment, les échanges remplacés, le résumé et les éléments conservés à l'identique. |
| Confirmation | `POST /conversations/{id}/confirmation` avec `{ "confirme": true }`. Le tour suivant reçoit `confirmation=True` (atelier 10b). L'événement `confirmation_demandee` précède le geste. |
| Limites | Champ optionnel `limites` de `POST /conversations` (`duree_s`, `budget_jetons`), transmis au *harness* (atelier 10d). |
