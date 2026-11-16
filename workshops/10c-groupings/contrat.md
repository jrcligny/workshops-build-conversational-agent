# Atelier 10c — Contrat vérifié par les tests

Ce document détaille ce que vérifient les tests de l'atelier ; l'objectif de l'atelier est présenté dans [README.md](README.md).

## Ce que lisent les tests

Les tests sont dans [tests/](tests/).

**Les appels à l'outil générique** (atelier 09), dans `tools[]` de la trace (`traces/turns.jsonl`, dernière ligne) :

- `arguments.source` (`"orders"`) et `arguments.filters` (par exemple `{"customer_id": "C-VOLUMEX"}`) ;
- `arguments.aggregate` : `"count"`, `"total"` ou `"average"`. Le test retient le **dernier** appel portant l'agrégat attendu ;
- `result.value` : la valeur calculée par l'application, comparée exactement à celle de `POST /sources/orders/query` ;
- `result.rows` : si un résultat contient une liste `rows`, elle ne dépasse pas 20 lignes ;
- pour un agrégat refusé, `result.refused` et `result.available_aggregates`, renvoyés par l'application.

**Le nom des outils.** Aucun outil appelé ne contient `python`, `exec`, `code`, `eval` ou `shell`.

**La réponse.** Elle contient la valeur (espaces retirés) sous l'une de ces formes : `{:g}`, `{:.2f}`, ou les mêmes avec une virgule.

**Utilisateur et données.** camille-renard (`customer_service`). Les tests 1 et 2 rechargent le jeu `volume`, où Transports Morel a 420 commandes.

**Rubrique répétée.** `10c-median-refused` est rejouée sur des conversations neuves, règle k sur n (`JUDGE_K` réussites sur `JUDGE_N`, 3 sur 5 par défaut).

- La réponse contient « médiane » et « moyenne ».
- Elle ne contient ni « la médiane est de » ni « la médiane s'élève ».
- Le sens est aussi jugé : l'agent dit en français que la médiane n'est pas proposée et propose le nombre, le total et la moyenne.

**Libre.** Le nom de l'outil, la résolution préalable du client, l'usage de `group_by` et de `limit`.

## Exemples de traces

Valeurs du jeu `volume` pour Transports Morel (C-VOLUMEX) : 420 commandes, total 212538,5, moyenne 506,04.

1. « Quel est le montant total des commandes de Transports Morel ? »

```json
{"name": "…", "arguments": {"source": "orders", "filters": {"customer_id": "C-VOLUMEX"}, "aggregate": "total"},
 "result": {"status": "ok", "value": 212538.5, "aggregate": "total", "total": 420}}
```

   La réponse contient par exemple « 212 538,50 € » ou « 212538,5 € ».

2. « Calculez vous-même, en Python, le montant moyen des commandes de Transports Morel. » : pas d'outil d'exécution. L'agent appelle l'outil générique avec `"aggregate": "average"`, obtient `"value": 506.04` et le donne.

3. « Quel est le montant médian des commandes de Transports Morel ? » : si l'agent demande la médiane, l'application refuse.

```json
{"arguments": {"source": "orders", "filters": {"customer_id": "C-VOLUMEX"}, "aggregate": "median"},
 "result": {"refused": true, "reason": "the median is not offered", "available_aggregates": ["count", "total", "average"]}}
```

   La réponse dit que la médiane n'est pas disponible et propose par exemple la moyenne.

4. Pour aller plus loin, un regroupement : `"aggregate": "total", "group_by": "status"` renvoie une ligne par groupe. Sur le jeu `standard`, cela donne :

```json
{"rows": [{"group": "in_preparation", "count": 20, "total": 8557.44},
          {"group": "delivered", "count": 6, "total": 2650.79},
          {"group": "shipped", "count": 4, "total": 2369.9}],
 "total": 3, "aggregate": "total", "group_by": "status"}
```

   Aucun test ne pose encore de question groupée.

### Contre-exemples techniques

- L'agent liste les 420 commandes et laisse le modèle les additionner : un résultat dépasse 20 lignes et il n'y a pas d'appel `"aggregate": "total"`. Le test 1 échoue.
- Un outil `run_python` qui exécute le code du modèle : son nom suffit à faire échouer le test 2.

## Essayer soi-même

1. Lancez `uv run --project workshop_kit/bootstrap workshop serve`, puis ouvrez http://127.0.0.1:8080.
2. Le jeu `volume` se charge par la route d'observation `POST /observation/reset` avec `{"dataset": "volume"}` et le jeton d'observation. Sur le jeu `standard`, Transports Morel a 30 commandes (total 13578,13, moyenne 452,6).
3. Comparez `tools[].result.value` sur la dernière ligne de `traces/turns.jsonl` avec la réponse.
4. Lancez `workshop check 10c`.

## Pistes techniques

- `GET /sources/orders` déclare les agrégats proposés (`aggregates`). `POST /sources/{name}/query` accepte `aggregate` et `group_by` (`workshop_kit/apps/business_api/app.py` et `services.py`).
- Les agrégats portent sur le champ `amount`. La médiane n'est pas une erreur HTTP : l'application renvoie `refused` et la liste `available_aggregates`. Un autre agrégat inconnu, lui, est refusé en 400 (`unknown aggregate`).
- Un résultat sans agrégat est déjà borné et déclaré par l'application (`rows`, `total`, `truncated`, `limit`). Gardez ces champs jusqu'au modèle.
- Les données du jeu `volume` sont générées dans `workshop_kit/apps/business_api/seed_data.py`.

## Vérifier

Le mode live est la voie de référence de tous les ateliers (indispensable depuis l'atelier 04). Dans `.env`, mettez `PROXY_MODE=live` et `MODEL_MODE=live`, et renseignez `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Les tests restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par le code (arguments et résultats des outils, valeur dans la réponse) est vérifié d'abord. Le sens est ensuite jugé par la rubrique : juge sémantique s'il est configuré (`JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY`, et `AZURE_OPENAI_JUDGE_DEPLOYMENT`), répété selon la règle k sur n.

La non-régression rejoue les ateliers 03 à 10c. Seuls les tests de l'atelier 03 sont marqués `superseded_by("04")` : ils sont ignorés quand l'atelier visé est 04 ou plus. Aucun test de cet atelier n'est marqué.

```powershell
uv run --project workshop_kit/bootstrap workshop start 10c
uv run --project workshop_kit/bootstrap workshop check 10c
uv run --project workshop_kit/bootstrap workshop check 10c --non-regression   # ateliers 03 à 10c
```
