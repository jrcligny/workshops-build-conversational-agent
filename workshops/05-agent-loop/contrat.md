# Atelier 05 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.
Les tests portent le marqueur `etape("outils")` ou `etape("boucle")`.

## Ce que lisent les tests

### Étape `outils`

Les tests lisent `tools` dans la trace (`name`, `arguments`, `result.status`, `result`).
Sont imposés :

- « Quelles commandes de Léa Martin sont en retard ? » : les résultats `ok` contiennent
  `C-MARTIN-LILLE` et `C-MARTIN-LYON` ; la réponse cite Lille et Lyon ; elle ne contient
  pas `CMD-2010` (la commande d'une seule des deux clientes) ;
- jeu de données `volume`, « Combien de commandes en retard a Transports Morel ? » :
  un appel d'outil avec `arguments.filter == "late"` ; `result.total` ou `result.count`
  vaut 60 ; la réponse contient « 60 ».

Le test compare 60 au décompte calculé par l'API métier : le nombre doit venir de la
source, pas d'un comptage fait par le modèle.

Restent libres : les noms des outils, leurs descriptions, la forme des autres arguments
et la façon d'enchaîner recherche et liste. Cette étape n'a pas de rubrique *k sur n*.

### Étape `boucle`

Sont imposés dans la trace :

- `cycles` : nombre entier d'appels au modèle pendant le tour ;
- `tools[].cycle` : indice entier du cycle de chaque appel d'outil ;
- `cycle_limit_reached` : booléen ;
- `interrupted` : booléen, présent et à `false` quand le tour n'est pas interrompu.

Sont imposés dans le flux SSE :

- un événement `step` par appel d'outil, avec `data.cycle` et `data.tool`, qui reprend
  le nom technique de l'outil (la liste des `step.tool` égale la liste des noms dans
  `tools`) ;
- un événement `mention` quand la limite de cycles est atteinte ;
- un événement `interruption` quand le tour est interrompu, toujours suivi de `text`
  puis de `end` avec `ok: true`.

Les tests vérifient aussi : au moins deux cycles et deux outils, avec des indices
croissants, pour une question chaînée (rechercher la cliente, puis lister ses commandes), et un dernier cycle (la réponse) après le dernier appel ; deux outils différents dans un même cycle pour
une question groupée ; ces deux comportements, choisis par le modèle, sont vérifiés sur des conversations neuves jusqu'à `JUDGE_K` réussites sur `JUDGE_N` ; aucun outil ni `step` quand l'interruption est demandée avant
le tour.

Restent libres : la valeur de la limite, la stratégie de groupement, les libellés métier
affichés à l'utilisateur et la formulation des réponses.

Rubrique `05-cycle-limit-partial` : la réponse contient « partiel », « partielle »,
« incomplet » ou « incomplète », et jamais « revue complète effectuée » ni « toutes les
commandes ont été vérifiées ». Elle est appliquée *k sur n* : `JUDGE_K` réussites
(3 par défaut) sur `JUDGE_N` essais (5 par défaut).

## Exemples techniques

### Étape `outils`

« Quelles commandes de Léa Martin sont en retard ? » → « Deux clientes portent ce nom, l'une
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

### Étape `boucle`

« Quelles commandes de Léa Martin, celle de Lille, sont en retard ? » → recherche de la
cliente au cycle 0, liste de ses commandes en retard au cycle 1, puis « Léa Martin (Lille)
n'a aucune commande en retard : CMD-2010 est expédiée et attendue dans deux jours. »

```json
{"cycles": 3, "cycle_limit_reached": false, "interrupted": false,
 "tools": [{"name": "search_customers", "cycle": 0},
           {"name": "list_customer_orders", "arguments": {"filter": "late"}, "cycle": 1}]}
```

Événements SSE : `step` (`{"cycle": 0, "tool": "search_customers"}`), `step`, `text`, `end`.

« Faites une revue complète de toutes les commandes de Transports Morel, une par une,
en vérifiant le détail de chacune pour repérer les retards, sans vous arrêter. » → la limite est atteinte ;
événement `mention` ; « Revue partielle : j'ai vérifié 8 commandes sur 30. »

### Contre-exemples techniques

- Omettre `interrupted` dans la trace d'un tour normal.
- Enchaîner sur deux cycles deux appels indépendants : le test du groupement échoue.

## Essayer soi-même

```powershell
uv run --project tooling/cli workshop serve
```

Ouvrez http://127.0.0.1:8080, posez les questions du README, puis lisez la dernière ligne
de `traces/turns.jsonl`. Le jeu `standard` compte 4 retards pour Transports Morel ; le
test du décompte charge le jeu `volume` (60 retards).

L'interface Chainlit n'affiche ni `mention` ni `interruption` et n'a pas de bouton
d'interruption. Pour les voir, créez une conversation
(`POST http://127.0.0.1:8000/conversations`), demandez l'interruption
(`POST /conversations/{id}/interruption`), puis suivez le flux du tour suivant avec
`curl.exe -N` sur `/conversations/{id}/messages` et le corps `{"text": "..."}`.

## Pistes techniques

- `GET /customers?name=` cherche par nom ; `GET /customers/{id}/orders?filter=late`
  renvoie `orders`, `total`, `truncated` et `limit` (voir
  `business/business_api/src/business_api/app.py` et `services.py`).
- Prenez `total` dans la réponse de l'API, pas la longueur de la liste.
- `business_api(jeton).get(chemin, params={...})` de `agent_sdk/src/agent_sdk/http_client.py`
  passe les filtres en paramètres de requête ; `declare(fonction)` de
  `agent_sdk/src/agent_sdk/tool_schema.py` déclare chaque outil (un `Literal` devient un `enum`).
- Les données sont dans `business/business_api/src/business_api/seed_data.py` ; les assertions
  détaillées sont dans [tests/](tests/).
- Les types d'événements et le paramètre `interrupt_requested` sont décrits dans
  `agent_sdk/src/agent_sdk/contract.py` et `docs/interface-contract.md`. Les constructeurs
  `step(outil)`, `mention(texte)` et `interruption()` de `agent_sdk/src/agent_sdk/events.py`
  produisent des événements bien formés ; quand les émettre reste à vous.
- `gateway/agent_gateway/src/agent_gateway/chat_app.py` montre comment l'interface transmet l'interruption :
  `interrupt_requested` est fixé au début du tour (via `/interruption` ou le champ
  `"interrupt": true` du message). Consultez-le avant chaque cycle, avant tout outil.
- Pour atteindre la limite sur la revue de 30 commandes, elle doit rester inférieure au
  nombre de cycles qu'exige cette revue.
- Les assertions détaillées sont dans [tests/](tests/).

## Vérifier

Le mode live est nécessaire : `PROXY_MODE=live`, `MODEL_MODE=live`,
`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Les tests restent rouges tant que le critère n'est pas atteint. Les contrôles de code
passent d'abord, puis la rubrique. Le juge utilise `JUDGE_MODE`, `JUDGE_BASE_URL`,
`JUDGE_API_KEY` et `AZURE_OPENAI_JUDGE_DEPLOYMENT` pour sa couche de sens. Les
rubriques sont répétées *k sur n*.

La non-régression rejoue les ateliers 03 à 05 : l'outil de l'atelier 04 doit toujours
fonctionner. Les tests de l'atelier 03 marqués `superseded_by("04")` sont sautés.

```powershell
workshop start 05
workshop check 05 --etape outils     # première étape
workshop check 05 --etape boucle     # seconde étape
workshop check 05                    # les deux étapes
workshop check 05 --non-regression   # ateliers 03 à 05
```
