# Atelier 06 — Contrat vérifié par les tests

Ce document détaille ce que vérifient les tests de l'atelier ; l'objectif de l'atelier est présenté dans [README.md](README.md).

## Ce que lisent les tests

Les tests sont dans [tests/](tests/). Ils portent le marqueur `etape("serveur")` ou `etape("regroupements")`.

### Étape `serveur`

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

**Utilisateurs.** camille-renard (`customer_service`) par défaut ; nina-accountant (`accountant`, `organization-a`) pour les factures. Jeu de données `standard`. Cette étape n'a pas de rubrique jugée.

### Étape `regroupements`

**Les appels à l'outil générique**, dans `tools[]` de la trace :

- `arguments.aggregate` : `"count"`, `"total"` ou `"average"`. Pour un agrégat simple, le test retient le **dernier** appel portant l'agrégat attendu, et compare `result.value` exactement à celle de `POST /sources/orders/query` ;
- pour un regroupement, un appel porte un `arguments.group_by` non vide, et son `result` contient chacune des valeurs groupées calculées par l'application (`POST /sources/invoices/query` avec `group_by: ["supplier_id", "month"]`). La forme du résultat est libre (libellés, ordre), pas les montants ;
- aucun résultat d'outil ne contient de ligne de facture du jeu `volume` (références `FAC-H0…`) : les lignes ne sont pas rapatriées pour être regroupées par le modèle ;
- pour un agrégat refusé, `result.refused` et `result.available_aggregates`, renvoyés par l'application.

**Le nom des outils.** Aucun outil appelé ne contient `python`, `exec`, `code`, `eval` ou `shell`.

**La réponse.** Elle contient la valeur (espaces retirés) sous l'une de ces formes : `{:g}`, `{:.2f}`, ou les mêmes avec une virgule. Pour le regroupement, elle nomme les trois fournisseurs et donne le plus gros montant groupé.

**Utilisateurs et données.** leo-controller (`financial_controller`) pour le regroupement, camille-renard pour les autres. Les tests rechargent le jeu `volume` : Transports Morel y a 420 commandes, et trois fournisseurs (Papeterie Atlantique, Bureau Plus, Transit Ouest) y ont des factures réglées sur les trois derniers mois.

**Rubrique répétée.** `06-median-refused` est rejouée sur des conversations neuves, règle k sur n (`JUDGE_K` réussites sur `JUDGE_N`, 3 sur 5 par défaut). La réponse contient « médiane » et « moyenne », ne contient ni « la médiane est de » ni « la médiane s'élève », et le sens est jugé : l'agent dit que la médiane n'est pas proposée et propose le nombre, le total et la moyenne.

**Libre.** Le nom de l'outil, la résolution préalable du client ou du fournisseur, l'usage de `limit`, la façon d'exposer `group_by` dans le schéma de l'outil.

## Exemples de traces

### Étape `serveur`

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

### Étape `regroupements`

1. Avec leo-controller, « Quelle est la répartition des montants facturés par fournisseur et par mois ? » :

```json
{"arguments": {"source": "invoices", "aggregate": "total", "group_by": ["supplier_id", "month"]},
 "result": {"status": "ok", "rows": [{"group": {"supplier_id": "F-BUREAU", "month": "…"}, "count": 2, "total": 1200.0}, "…"]}}
```

   La réponse présente chaque fournisseur par son nom, mois par mois, avec les montants de l'application.

2. « Calculez vous-même, en Python, le montant moyen des commandes de Transports Morel. » : pas d'outil d'exécution. L'agent appelle l'outil générique avec `"aggregate": "average"`, obtient `"value": 506.04` et le donne.

3. « Quel est le montant médian des commandes de Transports Morel ? » : si l'agent demande la médiane, l'application refuse.

```json
{"arguments": {"source": "orders", "filters": {"customer_id": "C-VOLUMEX"}, "aggregate": "median"},
 "result": {"refused": true, "reason": "the median is not offered", "available_aggregates": ["count", "total", "average"]}}
```

### Contre-exemples techniques (les deux étapes)

- Le harnais appelle encore ses outils Python en direct : `transport` n'est pas `"mcp"`, le test 2 échoue.
- Le serveur relaie le filtre `DELIV` tel quel : l'application ne le rejette pas, elle renvoie zéro ligne (`"rows": []`). Sans erreur `"status": "error"`, le test 3 échoue.
- Le modèle additionne lui-même les montants des factures : sans `"aggregate": "total"`, le test 4 échoue même si le nombre est juste.
- Un catalogue qui dépend du client ou de l'ordre des connexions échoue au test 1.
- L'agent liste les factures et laisse le modèle les regrouper : des lignes `FAC-H0…` apparaissent dans un résultat, le test du regroupement échoue.
- Un outil `run_python` qui exécute le code du modèle : son nom suffit à faire échouer le test sans exécution de code.

## Essayer soi-même

1. Lancez `uv run --project tooling/cli workshop serve`. Le serveur MCP de `my-agent/` écoute sur le port 8004, et le harnais reçoit `MCP_URL=http://127.0.0.1:8004/mcp`.
2. Pour lancer le serveur seul : `uv run --project my-agent python my-agent/mcp_server.py`.
3. Ouvrez http://127.0.0.1:8080, posez les questions ci-dessus, puis lisez `tools[]` sur la dernière ligne de `traces/turns.jsonl`.
4. Le jeu `volume` se charge par `POST /observation/reset` avec `{"dataset": "volume"}` et le jeton d'observation.
5. Lancez `workshop check 06 --etape serveur`, puis `workshop check 06 --etape regroupements`.

## Pistes techniques

- Partez de la coquille `my-agent/mcp_server.py` : `create_server()`, `application()`, `MCP_PATH`, SDK officiel `mcp`. Dans le serveur, `agent_sdk.http_client` joint l'API métier.
- Côté *harness*, `agent_sdk/src/agent_sdk/mcp_client.py` fournit `list_tools()`, `call_tool()` et `as_openai_tool()` (adresse lue dans `MCP_URL`), avec la liste de vérification du branchement dans sa docstring. Le catalogue d'outils et le champ `transport: "mcp"` de la trace restent à vous.
- Les routes génériques sont dans `business/business_api/src/business_api/app.py` : `GET /sources`, `GET /sources/{name}` (champs, valeurs codées, agrégats) et `POST /sources/{name}/query` (`filters`, `limit`, `aggregate`, `group_by`). Une clé de filtre inconnue est refusée (400), mais pas une valeur codée invalide : la vérification revient au serveur MCP.
- Pendant `workshop check`, les tests de cet atelier démarrent votre serveur MCP et transmettent son adresse au harnais par `MCP_URL`, comme `workshop serve`. Lisez `MCP_URL` à chaque tour ; les adresses des autres services arrivent de la même façon (`BUSINESS_API_URL`, `DOCS_SEARCH_URL`, `PROXY_URL`). Pour les tests d'autres ateliers, où `MCP_URL` n'est pas définie, le harnais démarre ou joint lui-même son serveur.
- Le chargement du module est fait par `gateway/agent_gateway/src/agent_gateway/loader.py` (`load_mcp_server`).
- Les questions des factures demandent le rôle `accountant` ou `financial_controller`.
- `GET /sources/{name}` déclare les agrégats proposés (`aggregates`) et le champ de date (`date_field`). `group_by` accepte un champ ou une liste de champs, dont `month` (mois de ce champ de date). La médiane n'est pas une erreur HTTP : l'application renvoie `refused` et `available_aggregates`.
- Un résultat sans agrégat est déjà borné et déclaré par l'application (`rows`, `total`, `truncated`, `limit`). Gardez ces champs jusqu'au modèle.

## Vérifier

Le mode live est la voie de référence de tous les ateliers (indispensable depuis l'atelier 04). Dans `.env`, mettez `PROXY_MODE=live` et `MODEL_MODE=live`, et renseignez `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Les tests restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par le code (catalogue, trace, journal de l'application) est vérifié d'abord. L'étape `serveur` n'a pas de rubrique de sens ; l'étape `regroupements` en a une.

Les rubriques sont jugées par un juge sémantique s'il est configuré (`JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY`, `AZURE_OPENAI_JUDGE_DEPLOYMENT`) et répétées selon la règle k sur n.

La non-régression rejoue les ateliers 03 à 06. Seuls les tests de l'atelier 03 sont marqués `superseded_by("04")`. Attention : les tests de l'atelier 05 lisent toujours leurs propres noms d'arguments (`arguments.filter` = `"late"`, deux appels distincts dans un même cycle). Vérifiez que votre catalogue MCP les satisfait encore.

```powershell
uv run --project tooling/cli workshop start 06
uv run --project tooling/cli workshop check 06 --etape serveur
uv run --project tooling/cli workshop check 06 --etape regroupements
uv run --project tooling/cli workshop check 06 --non-regression   # ateliers 03 à 06
```
