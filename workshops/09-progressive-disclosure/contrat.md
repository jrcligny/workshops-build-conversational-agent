# Atelier 09 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.

## Ce que lisent les tests

Tous les tests rechargent le jeu `volume` (Transports Morel, C-VOLUMEX : 420 commandes, dont 60 en retard). Utilisateur : camille-renard (`customer_service`, organization-a).

Les tests lisent l'outil d'interrogation générique de l'atelier 06 : un appel de `tools[]` avec `arguments.source == "orders"`. Pour une liste (ni `aggregate`, ni `group_by`), le dernier appel dont `result.rows` est une liste de lignes est retenu :

- `rows` : au plus 20 lignes, chacune avec sa `reference` et sans champ de détail (`amount`, `delivery_city`, `delivery_date`, `customer_id`, `organization_id`, `deleted`) ;
- `returned` : le nombre de lignes de cette portion (égal à la longueur de `rows`) ;
- `total` et `total_status` : `60` et `"exact"` pour les retards ; `200` et `"minimum"` pour toutes les commandes, car l'application ne récupère pas plus de 200 lignes ;
- `truncated` : `true` quand la liste est coupée.

Les tests vérifient aussi :

- **liste bornée** (« Quelles sont les commandes en retard de Transports Morel ? ») : les champs ci-dessus, « 60 » dans la réponse, et `model.calls[].context_size` entier positif pour chaque appel au modèle (au moins deux) ;
- **portion suivante** (même question, puis « Montrez-moi les suivantes. ») : le second tour relit une liste dont aucune `reference` n'était dans la première ;
- **plafond** (« Listez toutes les commandes de Transports Morel. ») : `total` 200, `total_status` `"minimum"`, et la réponse contient « 200 » et « au moins », « plus de » ou « minimum » ;
- **décompte** : un appel avec `arguments.aggregate == "count"` renvoie `result.value` à 60, sans `rows`, et la réponse contient « 60 » ;
- **détail** (conversation chargée où la liste a déjà été montrée — appels écrits `resolve_name` puis `query`, jeu `volume`, voir `docs/interface-contract.md` —, puis seul tour joué « Quel est le montant de la première commande de cette liste ? ») : le journal de l'API métier contient `GET /orders/<référence de la première ligne>`, et la réponse donne son montant, avec deux décimales (point ou virgule).

Les tests privés ajoutent un **regroupement volumineux** : un appel avec `arguments.group_by` non vide sur `"source": "orders"` (par exemple un groupe par jour de commande, 86 groupes) renvoie au plus 20 `rows`, avec `returned`, `total` (le nombre de groupes calculé par l'application), `total_status` `"exact"` et `truncated` `true`, et la réponse donne ce nombre.

Rubrique `09-partial-result-announced` sur la liste bornée : la réponse contient « partiel », « partielle », « une partie », « extrait » ou « premières ». Elle est appliquée une seule fois, pas en *k sur n*.

Restent libres : le nom de l'outil et de ses paramètres (y compris celui de la position), la limite d'affichage tant qu'elle ne dépasse pas 20, les champs résumés autres que `reference`, et la mesure de taille utilisée.

Les conversations chargées appellent des outils aux noms neutres (`resolve_name`, `query`) que votre agent ne propose pas forcément : il doit les rejouer tels quels.

## Exemples techniques

« Quelles sont les commandes en retard de Transports Morel ? » → « Voici les 20 premières des 60 commandes en retard ; voulez-vous la suite ? »

```json
{"name": "query_data", "arguments": {"source": "orders", "filters": {"customer_id": "C-VOLUMEX", "late": true}},
 "result": {"status": "ok", "rows": [{"reference": "CMD-V0007", "order_date": "…", "status": "shipped", "promised_date": "…"}, "…"],
            "returned": 20, "total": 60, "total_status": "exact", "truncated": true, "next_offset": 20}}
```

« Montrez-moi les suivantes. » → un nouvel appel avec une position (par exemple `"offset": 20`) renvoie `CMD-V0294`… sans répéter les vingt premières.

« Listez toutes les commandes de Transports Morel. » → `{"total": 200, "total_status": "minimum", …}` et « au moins 200 commandes ».

« Combien de commandes en retard a Transports Morel ? Je veux seulement le nombre, pas les lignes. » → `{"arguments": {"source": "orders", "filters": {…, "late": true}, "aggregate": "count"}, "result": {"status": "ok", "value": 60}}`.

### Contre-exemples techniques

- Des lignes qui gardent `amount` ou `delivery_city` : la liste n'est pas résumée.
- `total` calculé sur les lignes affichées (20) au lieu du total de l'application (60).
- `total_status` `"exact"` à 200 alors que l'application a atteint son plafond.
- La portion suivante obtenue en relisant la liste depuis le début : les références se répètent.
- Un décompte obtenu en faisant venir les lignes puis en les comptant.

## Essayer soi-même

```powershell
uv run --project tooling/cli workshop serve
```

Chargez le jeu `volume` par la route d'observation `POST /observation/reset` avec `{"dataset": "volume"}` et le jeton d'observation, ouvrez http://127.0.0.1:8080, posez les questions du README, puis lisez la dernière ligne de `traces/turns.jsonl` (`tools`, `model.calls[].context_size`). Lancez enfin `workshop check 09`.

## Pistes techniques

- `POST /sources/{name}/query` accepte `filters`, `limit`, `offset`, `aggregate` et `group_by`. Sur `orders`, le filtre calculé `late` (booléen) garde les commandes en retard. Une liste ou un regroupement renvoie `rows`, `total`, `total_status` (`exact` ou `minimum` au-delà de 200 lignes), `truncated`, `limit`, `offset` et `next_offset` ; voir `business/business_api/src/business_api/services.py`.
- L'application renvoie les lignes complètes et accepte n'importe quelle `limit` : la limite d'affichage, le résumé des lignes et `returned` sont à votre charge.
- `GET /resolution?type=customer&name=…` résout le nom du client ; `GET /orders/{reference}` donne le détail d'une commande.
- Mesurez `context_size` juste avant chaque appel au modèle et enregistrez-le dans la trace du tour (`tracer.call_model(..., context_size=...)` ou `tracer.model_call(...)`, `agent_sdk/src/agent_sdk/trace.py`).
- Les assertions détaillées sont dans [tests/](tests/).

## Vérifier

Le mode live est nécessaire : `PROXY_MODE=live`, `MODEL_MODE=live`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Les tests restent rouges tant que le critère n'est pas atteint. Les contrôles de code passent d'abord, puis la rubrique. Le juge utilise `JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY` et `AZURE_OPENAI_JUDGE_DEPLOYMENT` pour sa couche de sens. Les rubriques des ateliers précédents sont répétées *k sur n*.

La non-régression rejoue les ateliers 03 à 09. Les tests de l'atelier 03 marqués `superseded_by("04")` sont sautés.

```powershell
workshop start 09
workshop check 09
workshop check 09 --non-regression   # ateliers 03 à 09
```
