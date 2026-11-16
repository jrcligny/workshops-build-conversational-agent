# Atelier 05 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.

## Ce que lisent les tests

Les tests lisent `tools` dans la trace (`name`, `arguments`, `result.status`, `result`).
Sont imposés :

- « Quelles sont les commandes de Léa Martin ? » : les résultats `ok` contiennent
  `C-MARTIN-LILLE` et `C-MARTIN-LYON` ; la réponse cite Lille et Lyon ; elle ne contient
  pas `CMD-2010` (la commande d'une seule des deux clientes) ;
- jeu de données `volume`, « Combien de commandes en retard a Transports Morel ? » :
  un appel d'outil avec `arguments.filter == "late"` ; `result.total` ou `result.count`
  vaut 60 ; la réponse contient « 60 ».

Le test compare 60 au décompte calculé par l'API métier : le nombre doit venir de la
source, pas d'un comptage fait par le modèle.

Restent libres : les noms des outils, leurs descriptions, la forme des autres arguments
et la façon d'enchaîner recherche et liste. Cet atelier n'a pas de rubrique *k sur n*.

## Exemples techniques

« Quelles sont les commandes de Léa Martin ? » → « Deux clientes portent ce nom, l'une
à Lille, l'autre à Lyon. Laquelle souhaitez-vous ? » Extrait de trace :

```json
{"name": "search_customers", "arguments": {"name": "Léa Martin"},
 "result": {"status": "ok", "customers": [{"id": "C-MARTIN-LILLE"}, {"id": "C-MARTIN-LYON"}]}}
```

« Combien de commandes en retard a Transports Morel ? » (jeu `volume`) → « Transports
Morel a 60 commandes en retard. »

```json
{"name": "list_customer_orders", "arguments": {"customer_id": "C-VOLUMEX", "filter": "late"},
 "result": {"status": "ok", "total": 60}}
```

Événements SSE : des `text`, puis `end` avec `ok: true`.

### Contre-exemples techniques

- Choisir la cliente de Lille et lister CMD-2010 : l'agent a tranché à la place de
  l'utilisateur.
- Lister toutes les commandes et laisser le modèle compter les retards : le nombre est
  fragile et l'argument `filter` manque.

## Essayer soi-même

```powershell
uv run --project workshop_kit/bootstrap workshop serve
```

Ouvrez http://127.0.0.1:8080, posez les questions du README, puis lisez la dernière ligne
de `traces/turns.jsonl`. Le jeu `standard` compte 4 retards pour Transports Morel ; le
test charge le jeu `volume` (60 retards). Lancez enfin `workshop check 05`.

## Pistes techniques

- `GET /customers?name=` cherche par nom ; `GET /customers/{id}/orders?filter=late`
  renvoie `orders`, `total`, `truncated` et `limit` (voir
  `workshop_kit/apps/business_api/app.py` et `services.py`).
- Prenez `total` dans la réponse de l'API, pas la longueur de la liste.
- `business_api(jeton).get(chemin, params={...})` de `agent_sdk/src/agent_sdk/http_client.py`
  passe les filtres en paramètres de requête ; `declare(fonction)` de
  `agent_sdk/src/agent_sdk/tool_schema.py` déclare chaque outil (un `Literal` devient un `enum`).
- Les données sont dans `workshop_kit/apps/business_api/seed_data.py` ; les assertions
  détaillées sont dans [tests/](tests/).

## Vérifier

Le mode live est nécessaire : `PROXY_MODE=live`, `MODEL_MODE=live`,
`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Les tests restent rouges tant que le critère n'est pas atteint. Les contrôles de code
passent d'abord, puis les rubriques. Le juge utilise `JUDGE_MODE`, `JUDGE_BASE_URL`,
`JUDGE_API_KEY` et `AZURE_OPENAI_JUDGE_DEPLOYMENT` pour sa couche de sens. Les
rubriques sont répétées *k sur n*.

La non-régression rejoue les ateliers 03 à 05 : l'outil de l'atelier 04 doit toujours
fonctionner. Les tests de l'atelier 03 marqués `superseded_by("04")` sont sautés.

```powershell
workshop start 05
workshop check 05
workshop check 05 --non-regression   # ateliers 03 à 05
```
