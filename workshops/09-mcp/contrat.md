# Atelier 09 — Contrat vérifié par les tests

Ce document détaille ce que vérifient les tests de l'atelier ; l'objectif de l'atelier est présenté dans [README.md](README.md).

## Ce que lisent les tests

Les tests sont dans [tests/](tests/).

**Le serveur MCP démarré par le test.** Le test charge lui-même `my-agent/mcp_server.py`, sans passer par `workshop serve` :

- il appelle la fonction `application()` du module, qui doit renvoyer l'application web du serveur ;
- il la lance avec uvicorn sur un port libre de `127.0.0.1`, dans un fil d'exécution ;
- il construit l'URL `http://127.0.0.1:<port>` suivie de la constante `MCP_PATH` du module (`/mcp` dans la coquille) ;
- il se connecte deux fois avec le client du SDK `mcp`, en transport HTTP streamable, et appelle `list_tools()`.

Gardez donc `application()` et `MCP_PATH`. La coquille les fournit déjà, avec un serveur sans état (`stateless_http=True`).

**Le catalogue.**

- Il n'est pas vide, et deux clients obtiennent les mêmes noms dans le même ordre.
- Aucun outil ne s'appelle `search_customer`, `search_customers`, `list_orders` ou `list_customer_orders`.
- Au moins un outil a un `inputSchema.properties` qui contient `source` et `filters`. `aggregate`, `group_by` et `limit` sont optionnels.
- Libres : le nom de l'outil générique, les autres outils (découverte, résolution de noms, consultation d'une commande).

**La trace du tour** (`traces/turns.jsonl`, dernière ligne).

- `tools[].transport` vaut `"mcp"` pour chaque appel.
- `tools[].name` appartient au catalogue.
- `tools[].arguments.source`, `tools[].arguments.filters` et `tools[].arguments.aggregate`.
- `tools[].result.status` : `"error"` sur un filtre rejeté (`"ok"`, ou son synonyme `"found"`, pour un succès).
- `tools[].result.error` cite les valeurs permises (`delivered`, `shipped`…).
- `tools[].result.value` : la valeur agrégée renvoyée par l'application.

**Le journal de l'application.** Au moins une route commence par `/sources/` (par exemple `POST /sources/orders/query`).

**Utilisateurs.** camille-renard (`customer_service`) par défaut ; nina-accountant (`accountant`, `organization-a`) pour les factures. Jeu de données `standard`. Aucune rubrique jugée dans cet atelier.

## Exemples de traces

1. « Combien de commandes a Martin Durand ? » : au moins un appel, tous en `"transport": "mcp"`. Pour camille, Martin Durand a une commande visible (CMD-1042).

```json
{"tools": [{"name": "…", "transport": "mcp",
            "arguments": {"source": "orders", "filters": {"customer_id": "C-DURAND-1"}, "aggregate": "count"},
            "result": {"status": "ok", "value": 1}}]}
```

2. « Listez les commandes dont le statut vaut DELIV. » : le premier appel est rejeté, puis l'agent corrige son filtre ou demande quel statut est visé.

```json
{"tools": [
  {"arguments": {"source": "orders", "filters": {"status": "DELIV"}},
   "result": {"status": "error", "error": "unknown status DELIV; allowed values: delivered, shipped, in_preparation, …"}},
  {"arguments": {"source": "orders", "filters": {"status": "delivered"}}, "result": {"status": "ok"}}
]}
```

   La formulation de l'erreur est libre ; elle doit contenir `delivered` et `shipped`.

3. Avec nina-accountant, « Quel est le montant total des factures en attente d'approbation ? » : le dernier appel sur `"source": "invoices"` porte `"aggregate": "total"`. Sa `result.value` vaut 1280 (FAC-3301-BIS), et la réponse affiche 1280.

```json
{"arguments": {"source": "invoices", "filters": {"status": "pending"}, "aggregate": "total"},
 "result": {"status": "ok", "value": 1280.0}}
```

### Contre-exemples techniques

- Le harnais appelle encore ses outils Python en direct : `transport` n'est pas `"mcp"`, le test 2 échoue.
- Le serveur relaie le filtre `DELIV` tel quel : l'application ne le rejette pas, elle renvoie zéro ligne (`"rows": []`). Sans erreur `"status": "error"`, le test 3 échoue.
- Le modèle additionne lui-même les montants des factures : sans `"aggregate": "total"`, le test 4 échoue même si le nombre est juste.
- Un catalogue qui dépend du client ou de l'ordre des connexions échoue au test 1.

## Essayer soi-même

1. Lancez `uv run --project workshop_kit/bootstrap workshop serve`. Le serveur MCP de `my-agent/` écoute sur le port 8004, et le harnais reçoit `MCP_URL=http://127.0.0.1:8004/mcp`.
2. Pour lancer le serveur seul : `uv run --project my-agent python my-agent/mcp_server.py`.
3. Ouvrez http://127.0.0.1:8080, posez les questions ci-dessus, puis lisez `tools[]` sur la dernière ligne de `traces/turns.jsonl`.
4. Lancez `workshop check 09`.

## Pistes techniques

- Partez de la coquille `my-agent/mcp_server.py` : `create_server()`, `application()`, `MCP_PATH`, SDK officiel `mcp`.
- Les routes génériques sont dans `workshop_kit/apps/business_api/app.py` : `GET /sources`, `GET /sources/{name}` (champs, valeurs codées, agrégats) et `POST /sources/{name}/query` (`filters`, `limit`, `aggregate`, `group_by`). Une clé de filtre inconnue est refusée (400), mais pas une valeur codée invalide : la vérification revient au serveur MCP.
- Pendant `workshop check`, les tests de cet atelier démarrent votre serveur MCP et transmettent son adresse au harnais par `MCP_URL`, comme `workshop serve`. Lisez `MCP_URL` à chaque tour ; les adresses des autres services arrivent de la même façon (`BUSINESS_API_URL`, `DOCS_SEARCH_URL`, `PROXY_URL`). Pour les tests d'autres ateliers, où `MCP_URL` n'est pas définie, le harnais démarre ou joint lui-même son serveur.
- Le chargement du module est fait par `workshop_kit/shell/loader.py` (`load_mcp_server`).
- La question des factures demande le rôle `accountant`.

## Vérifier

Le mode live est la voie de référence de tous les ateliers (indispensable depuis l'atelier 04). Dans `.env`, mettez `PROXY_MODE=live` et `MODEL_MODE=live`, et renseignez `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Les tests restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par le code (catalogue, trace, journal de l'application) est vérifié d'abord. Cet atelier n'a pas de rubrique de sens. Ailleurs, une rubrique est jugée par un juge sémantique s'il est configuré (`JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY`), et répétée selon la règle k sur n (`JUDGE_K` réussites sur `JUDGE_N` essais).

La non-régression rejoue les ateliers 03 à 09. Seuls les tests de l'atelier 03 sont marqués `superseded_by("04")` : ils sont ignorés quand l'atelier visé est 04 ou plus. Aucun test de cet atelier n'est marqué. Attention : les tests des ateliers précédents lisent toujours leurs propres noms d'arguments. L'atelier 05 attend `arguments.filter` = `"late"`, l'atelier 07 attend une liste `result.orders` résumée avec `returned`, `total`, `total_status` et `truncated`, une position pour la portion suivante, et `arguments.mode` = `"count"` avec `result.count`, et l'atelier 06 attend deux noms d'outils distincts pour deux appels indépendants. Vérifiez que votre catalogue MCP les satisfait encore.

```powershell
uv run --project workshop_kit/bootstrap workshop start 09
uv run --project workshop_kit/bootstrap workshop check 09
uv run --project workshop_kit/bootstrap workshop check 09 --non-regression   # ateliers 03 à 09
```
