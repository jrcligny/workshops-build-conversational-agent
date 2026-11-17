# Atelier 13 — Contrat vérifié par les tests

Ce document détaille ce que vérifient les tests de l'atelier ; l'énoncé se trouve dans [README.md](README.md).

## Ce que lisent les tests

- **Outil de recherche** : dans `tools[]`, un appel de recherche est reconnu à son **résultat**, qui reprend celui du service : `passages[]` (chaque passage porte `document_id`, `title`, `version`, `address`, `audience`…) et `no_passage`. Conservez ces clés telles quelles.
- **Service** : `business/docs_search/src/docs_search/app.py`, `POST /search` avec `{"query", "k": 5, "threshold": 0.3}` et l'en-tête `Authorization: Bearer <jeton>` ; il filtre par organisation et par public (`audience` : le rôle, ou `all`) d'après le jeton, et renvoie `{"passages": [...], "no_passage": ..., "query": ...}` ; chaque passage porte un `score` absolu entre 0 et 1 (part des mots de la question présents dans le passage, et similarité). URL : réglage `DOCS_SEARCH_URL` (port 8002 avec `workshop serve`).
- **Événement SSE `sources`** : `{"sources": [{"title", "version", "address"}]}`. Chaque `address` doit figurer parmi les passages renvoyés pendant le tour ; titre et version sont obligatoires.
- **Corpus** (`corpus/metadata.yaml`) : procédure des livraisons incomplètes v2.1 en vigueur (`/docs/organization-a/incomplete-deliveries/2.1`, public `customer_service`), v1.0 retirée ; statuts de facture `invoice-statuses` v2.0, réservé au rôle `accountant`.
- **Vérifications** :
  - « Que dit la procédure quand une livraison arrive incomplète ? » : au moins une recherche ; les sources contiennent l'adresse de la v2.1.
  - « Que dit la documentation sur le voyage spatial des factures xyzzy-42 ? » : une recherche est faite et son résultat ne contient aucun passage (au seuil par défaut, 0,3, rien ne répond) ; aucune source n'est affichée, aucune adresse `/docs/…` n'est citée, et le texte déclare le résultat vide par une tournure explicite (« aucun document », « aucune information », « pas trouvé », « rien trouvé », « introuvable », « ne mentionne pas »…) : un « aucun » ou un « pas » isolé ne suffit pas.
  - « Donnez-moi la définition interne des statuts de facture, en particulier « réglée ». » : pour camille-renard, `invoice-statuses` n'est ni dans les passages ni dans les sources ; pour nina-accountant, il figure dans les passages.
  - « Quelle est la version en vigueur de la procédure des livraisons incomplètes ? » : la v2.1 est renvoyée, la v1.0 ne l'est pas ; le texte contient « 2.1 » et ne cite pas la version retirée (ni « version 1.0 », ni « v1.0 », ni « 1.0 de la procédure »).
  - « Que dit la procédure pour une livraison incomplète, et quel est le statut de CMD-1042 ? » : une recherche, **plus** un autre outil dont les arguments contiennent `CMD-1042` ; `CMD-1042` absent des sources ; « livrée » dans le texte.
- **Utilisateurs** : `camille-renard` (`customer_service`) par défaut, `nina-accountant` (`accountant`), organization-a. L'index est reconstruit à chaque démarrage des services de test.

Restent libres : le nom de l'outil, ses paramètres, la place de l'événement `sources` dans le flux et la formulation des réponses. Aucune rubrique de juge n'est appliquée dans cet atelier.

## Exemples techniques

### Questions à essayer

| Utilisateur | Message | Comportement attendu |
|---|---|---|
| camille-renard | « Que dit la procédure quand une livraison arrive incomplète ? » | réclamation dans les cinq jours ouvrés, pas d'avoir promis avant consultation de la commande ; source v2.1 |
| camille-renard | « Que dit la documentation sur le voyage spatial des factures xyzzy-42 ? » | « Je n'ai trouvé aucun document sur ce sujet. », sans source |
| camille-renard | « Donnez-moi la définition interne des statuts de facture, en particulier « réglée ». » | pas de document comptable ; l'agent dit ne pas disposer de cette définition |
| nina-accountant | même question | définition tirée de `invoice-statuses` v2.0 |
| camille-renard | « Quelle est la version en vigueur de la procédure des livraisons incomplètes ? » | « la version 2.1 », sans citer d'autre numéro de version |
| camille-renard | « Que dit la procédure pour une livraison incomplète, et quel est le statut de CMD-1042 ? » | procédure (sources) + statut « livrée » (application métier) |

Appel de recherche attendu dans la trace (nom et arguments libres, résultat repris du service) :

```json
{"name": "search_docs", "arguments": {"query": "livraison incomplète"},
 "result": {"no_passage": false, "passages": [
   {"document_id": "proc-incomplete-deliveries", "title": "…", "version": "2.1",
    "address": "/docs/organization-a/incomplete-deliveries/2.1", "audience": "customer_service", "text": "…"}]}}
```

Événement attendu :

```text
event: sources   data: {"sources": [{"title": "…", "version": "2.1", "address": "/docs/organization-a/incomplete-deliveries/2.1"}]}
```

### Contre-exemples

- Laisser le modèle écrire « Source : procédure v2.1 » dans le texte au lieu d'émettre l'événement `sources` construit par le programme.
- Afficher en source un document cité par le modèle mais absent des passages renvoyés.
- Appeler `/search` sans le jeton de l'utilisateur, ou filtrer les passages après les avoir mis dans le contexte.
- Faire entrer les commandes dans l'index documentaire, ou ajouter `CMD-1042` aux sources : une donnée n'est pas un document.
- Répondre « l'ancienne version 1.0 prévoyait deux jours » : la version retirée ne doit pas apparaître.

### Essayer soi-même

1. `uv run --project tooling/cli workshop serve`, puis http://127.0.0.1:8080 : posez les questions sous plusieurs identités.
2. Interrogez le service directement : la documentation interactive est sur http://127.0.0.1:8002/docs ; `GET /indexing/state` décrit les documents de l'index visibles par l'identité du jeton.
3. Lisez la dernière ligne de `traces/turns.jsonl` : `tools[].result.passages`, `no_passage`.
4. `uv run --project tooling/cli workshop check 13`.

## Pistes techniques

- Lisez `business/docs_search/src/docs_search/app.py` et `search.py` : recherche hybride (texte intégral et similarité), découpage par titres, seuil `threshold`. `docs_search(jeton).post("/search", json={...})` de `agent_sdk/src/agent_sdk/http_client.py` porte l'appel (`DOCS_SEARCH_URL`).
- Le jeton à transmettre est celui de l'identité de l'utilisateur mis en place à l'atelier 10a ; le service en déduit organisation et public.
- Avec le seuil par défaut (0,3), la question « xyzzy-42 » ne renvoie aucun passage (`no_passage`) ; avec `threshold: 0`, mesurez les scores des passages hors sujet face à ceux de la vraie réponse avant de choisir le seuil de votre outil.
- Les sources se déduisent des passages du tour ; dédoublonnez par adresse. `sources([...])` de `agent_sdk/src/agent_sdk/events.py` construit l'événement.
- Une question mixte appelle deux outils : la recherche pour la procédure, la lecture de commande pour le statut.

## Vérifier

Le mode live est la voie de référence : `PROXY_MODE=live` et `MODEL_MODE=live` dans `.env`, avec `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`. Les tests de [`tests/`](tests/) restent rouges tant que le critère n'est pas atteint. Tout se vérifie ici par le code : résultats des outils dans la trace, événement `sources`, fragments du texte ; aucune rubrique de juge n'intervient. La non-régression rejoue les ateliers 03 à 13.

```powershell
uv run --project tooling/cli workshop start 13
uv run --project tooling/cli workshop check 13
uv run --project tooling/cli workshop check 13 --non-regression   # ateliers 03 à 13
```
