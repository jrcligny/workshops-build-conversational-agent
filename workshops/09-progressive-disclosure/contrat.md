# Atelier 09 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.

## Ce que lisent les tests

Tous les tests rechargent le jeu `volume` (Transports Morel, C-VOLUMEX : 420 commandes, dont 60 en retard). Utilisateur : camille-renard (`customer_service`, organization-a).

Résultat de l'outil de liste (`tools[].result`, dernier appel qui contient une liste `orders`) :

- `orders` : au plus 20 lignes, chacune avec sa `reference` et sans champ de détail (`amount`, `delivery_city`, `delivery_date`, `customer_id`, `organization_id`, `deleted`) ;
- `returned` : le nombre de lignes de cette portion (égal à la longueur de `orders`) ;
- `total` et `total_status` : `60` et `"exact"` pour les retards ; `200` et `"minimum"` pour toutes les commandes, car l'application ne récupère pas plus de 200 commandes ;
- `truncated` : `true` quand la liste est coupée.

Les tests vérifient aussi :

- **liste bornée** (« Quelles sont les commandes en retard de Transports Morel ? ») : les champs ci-dessus, « 60 » dans la réponse, et `model.calls[].context_size` entier positif pour chaque appel au modèle (au moins deux) ;
- **portion suivante** (même question, puis « Montrez-moi les suivantes. ») : le second tour relit une liste dont aucune `reference` n'était dans la première ;
- **plafond** (« Listez toutes les commandes de Transports Morel. ») : `total` 200, `total_status` `"minimum"`, et la réponse contient « 200 » et « au moins », « plus de » ou « minimum » ;
- **décompte** : un appel avec `arguments.mode == "count"` renvoie `result.count` à 60, sans lignes, et la réponse contient « 60 » ;
- **détail** (conversation chargée où la liste a déjà été montrée — appel `list_orders` écrit, jeu `volume`, voir `docs/interface-contract.md` —, puis seul tour joué « Quel est le montant de la première commande de cette liste ? ») : le journal de l'API métier contient `GET /orders/<référence de la première ligne>`, et la réponse donne son montant, avec deux décimales (point ou virgule).

Rubrique `09-partial-result-announced` sur la liste bornée : la réponse contient « partiel », « partielle », « une partie », « extrait » ou « premières ». Elle est appliquée une seule fois, pas en *k sur n*.

Restent libres : le nom des outils et de leurs paramètres (y compris celui de la position), la limite d'affichage tant qu'elle ne dépasse pas 20, les champs résumés autres que `reference`, et la mesure de taille utilisée.

## Exemples techniques

« Quelles sont les commandes en retard de Transports Morel ? » → « Voici les 20 premières des 60 commandes en retard ; voulez-vous la suite ? »

```json
{"name": "list_customer_orders", "arguments": {"customer_id": "C-VOLUMEX", "filter": "late"},
 "result": {"status": "ok", "orders": [{"reference": "CMD-V0007", "order_date": "…", "status": "shipped", "promised_date": "…"}, "…"],
            "returned": 20, "total": 60, "total_status": "exact", "truncated": true}}
```

« Montrez-moi les suivantes. » → un nouvel appel avec une position (par exemple `"position": 20`) renvoie `CMD-V0147`… sans répéter les vingt premières.

« Listez toutes les commandes de Transports Morel. » → `{"total": 200, "total_status": "minimum", …}` et « au moins 200 commandes ».

« Combien de commandes en retard a Transports Morel ? Je veux seulement le nombre, pas les lignes. » → `{"arguments": {"mode": "count", …}, "result": {"status": "ok", "count": 60}}`.

### Contre-exemples techniques

- Des lignes qui gardent `amount` ou `delivery_city` : la liste n'est pas résumée.
- `total` calculé sur les lignes affichées (20) au lieu du total de l'application (60).
- `total_status` `"exact"` à 200 alors que l'application a atteint son plafond.
- La portion suivante obtenue en relisant la liste depuis le début : les références se répètent.

## Essayer soi-même

```powershell
uv run --project tooling/cli workshop serve
```

Chargez le jeu `volume` par la route d'observation `POST /observation/reset` avec `{"dataset": "volume"}` et le jeton d'observation, ouvrez http://127.0.0.1:8080, posez les questions du README, puis lisez la dernière ligne de `traces/turns.jsonl` (`tools`, `model.calls[].context_size`). Lancez enfin `workshop check 09`.

## Pistes techniques

- `GET /customers/{id}/orders` accepte `filter`, `limit` et `offset`. Il renvoie `orders`, `total`, `total_status` (`exact` ou `minimum` au-delà de 200), `truncated`, `limit`, `offset` et `next_offset` ; voir `business/business_api/src/business_api/services.py`.
- `GET /orders/{reference}` donne le détail d'une commande.
- Mesurez `context_size` juste avant chaque appel au modèle et enregistrez-le dans la trace du tour (`tracer.call_model(..., context_size=...)` ou `tracer.model_call(...)`, `agent_sdk/src/agent_sdk/trace.py`).
- Les assertions détaillées sont dans [tests/](tests/).

## Vérifier

Le mode live est nécessaire : `PROXY_MODE=live`, `MODEL_MODE=live`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Les tests restent rouges tant que le critère n'est pas atteint. Les contrôles de code passent d'abord, puis la rubrique. Le juge utilise `JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY` et `AZURE_OPENAI_JUDGE_DEPLOYMENT` pour sa couche de sens. Les rubriques des ateliers précédents sont répétées *k sur n*.

La non-régression rejoue les ateliers 03 à 09. Les tests de l'atelier 03 marqués `superseded_by("04")` sont sautés.

```powershell
workshop start 07
workshop check 09
workshop check 09 --non-regression   # ateliers 03 à 09
```
