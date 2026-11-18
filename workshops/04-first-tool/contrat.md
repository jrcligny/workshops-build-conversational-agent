# Atelier 04 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.

## Ce que lisent les tests

Pour les questions sur CMD-1042, CMD-1402 et CMD-0881, chaque question doit produire exactement
un appel d'outil (côté modèle ; l'outil peut faire plusieurs requêtes HTTP), lu dans `tools`
de la trace. Pour chaque entrée de `tools`, sont imposés :

- `name` (nom technique libre) et `arguments` (un objet) ;
- `result.status`, parmi `ok`, `approximate`, `not_found` et `error` ;
- en cas de rapprochement : `result.status` vaut `not_found` avec `result.suggestions`
  (forme recommandée, celle des exemples), ou, toléré, `approximate` avec `result.order`.

Les tests vérifient aussi :

- CMD-1042 : `arguments` contient `CMD-1042`, statut `ok`, le résultat contient
  `delivered`, la réponse contient « livrée », et le tour fait au moins deux appels au
  modèle ;
- CMD-1402 : le résultat propose CMD-1042 ; la réponse cite les deux références, et ne
  dit pas « livrée » sans point d'interrogation ;
- CMD-0881 : statut `not_found`, sans `order` ni `suggestions`, et la réponse ne contient
  pas « supprim » ;
- `1042;DROP` : aucun appel à `/orders` sur l'API métier, et `tools` contient **au moins
  un** appel d'outil, tous avec le statut `error` (le format attendu est `CMD-NNNN`). Le
  modèle transmet la référence telle quelle à l'outil, qui la rejette : un agent qui répond
  sans appeler l'outil échoue à ce test ;
- au tour suivant de la même conversation, `input.history` rejoue le message assistant
  porteur de l'appel d'outil (`tool_calls`) et le message `tool` qui lui répond (même
  `tool_call_id`), dont le contenu porte le statut lu (`delivered`).

Restent libres : le nom de l'outil, sa description, la méthode de rapprochement et la
formulation des réponses. Cet atelier n'a pas de rubrique *k sur n*.

## Exemples techniques

« Quel est le statut de la commande CMD-1042 de Martin Durand ? » → le modèle demande
l'outil, puis répond « La commande CMD-1042 est livrée. » Appel et trace :

```json
{"name": "get_order", "arguments": {"reference": "CMD-1042"},
 "result": {"status": "ok", "order": {"reference": "CMD-1042", "status": "delivered"}}}
```

Événements SSE : des `text`, puis `end` avec `ok: true`.

« Quel est le statut de la commande CMD-1402 ? » → « Je ne trouve pas CMD-1402.
Pensiez-vous à CMD-1042 ? »

```json
{"result": {"status": "not_found", "suggestions": ["CMD-1042"]}}
```

« Quel est le statut de la commande 1042;DROP ? » → l'outil renvoie `{"status": "error"}`
sans appeler l'API.

### Contre-exemples techniques

- Deux appels d'outil pour une seule question : les tests en attendent exactement un.

## Essayer soi-même

```powershell
uv run --project tooling/cli workshop serve
```

Ouvrez http://127.0.0.1:8080, posez les questions du README, puis lisez la dernière ligne
de `traces/turns.jsonl`. Lancez enfin `uv run --project tooling/cli workshop check 04`.

## Pistes techniques

- L'API métier est décrite dans `business/business_api/src/business_api/app.py` :
  `GET /orders/{reference}` renvoie 404 pour une commande absente ou exclue. Elle exige un
  jeton applicatif (`business/business_api/src/business_api/auth.py`).
- L'API n'offre pas de recherche approchée : votre outil calcule lui-même les références
  candidates et ne garde que celles qui existent.
- Validez le format avant tout appel : une référence invalide ne doit jamais atteindre l'API.
- Les données de départ sont dans `business/business_api/src/business_api/seed_data.py`.
- Le harnais trouve les services dans les variables d'environnement `BUSINESS_API_URL`,
  `PROXY_URL` et `DOCS_SEARCH_URL`, définies par `workshop serve` comme par
  `workshop check` (ports différents : lisez-les au moment de l'appel).
- L'utilisateur remis au harnais porte un jeton d'entrée (`user.app_token`, `typ` = `entry`),
  que l'API métier refuse (401). Échangez-le contre un jeton applicatif avec
  `agent_sdk.http_client.exchange_entry_token` (route `POST /auth/exchange` de l'API métier),
  puis présentez ce dernier : `token = exchange_entry_token(user.app_token)`, puis
  `business_api(token).get(...)`. L'atelier 07 déplacera cet échange dans le serveur MCP.
- `agent_sdk/src/agent_sdk/http_client.py` porte le transport : `business_api(token).get("/orders/CMD-1042")`
  lit `BUSINESS_API_URL` à l'appel, envoie `Authorization: Bearer`, applique un délai et lève
  `ServiceError` (`status_code` 404, 401… ou `None` si le service est injoignable). Le choix
  de la route, la validation et l'interprétation restent à vous.
- `agent_sdk/src/agent_sdk/tool_schema.py` (`declare(fonction)`) construit la déclaration
  OpenAI d'un outil à partir d'une fonction annotée et de sa docstring. Le nom, la
  description, les paramètres et la validation restent à vous ; rien ne s'exécute seul.
- Le protocole d'appel d'outil (`tools`, `tool_calls`, message `tool`, second appel) est
  décrit pas à pas, avec un aller-retour JSON, dans le [README](README.md#le-tour-avec-outil-pas-à-pas).
- `tracer.tool_call(nom, arguments, résultat)` (`Tracer`, `agent_sdk/src/agent_sdk/trace.py`)
  enregistre chaque appel d'outil dans `tools` de la trace ; passez `tools=` à
  `tracer.call_model(...)` pour que les outils proposés soient tracés.
- `agent_sdk/src/agent_sdk/context.py` garde le contexte d'un tour à l'autre : enregistrez avec
  `ctx.record(...)` tous les messages du tour (utilisateur, assistant avec `tool_calls`,
  résultats `tool`, réponse finale), pas seulement le texte final ; `ctx.for_model(...)` les
  rejoue au tour suivant et `tracer.input(history=ctx.messages)` les reporte dans la trace.
- Les assertions détaillées sont dans [tests/](tests/).

## Vérifier

Le mode live, voie de référence de tous les ateliers, devient indispensable : `PROXY_MODE=live`,
`MODEL_MODE=live`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et
`AZURE_OPENAI_CHAT_DEPLOYMENT` (voir `.env.example`).

Les tests restent rouges tant que le critère n'est pas atteint. Les contrôles de code
passent d'abord, puis les rubriques des ateliers précédents en non-régression. Le juge
utilise `JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY` et
`AZURE_OPENAI_JUDGE_DEPLOYMENT` pour sa couche de sens. Les rubriques sont répétées
*k sur n*.

La non-régression rejoue les ateliers 03 et 04. Les trois tests de l'atelier 03 marqués
`superseded_by("04")` (aucun outil, refus sans source) sont sautés : l'agent a
désormais un outil et doit donner un statut sourcé.

```powershell
uv run --project tooling/cli workshop start 04
uv run --project tooling/cli workshop check 04
uv run --project tooling/cli workshop check 04 --non-regression   # ateliers 03 à 04
```
