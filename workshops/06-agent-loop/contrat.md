# Atelier 06 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.

## Ce que lisent les tests

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
croissants, pour une question chaînée ; deux outils différents dans un même cycle pour
une question groupée ; aucun outil ni `step` quand l'interruption est demandée avant
le tour.

Restent libres : la valeur de la limite, la stratégie de groupement, les libellés métier
affichés à l'utilisateur et la formulation des réponses.

Rubrique `06-cycle-limit-partial` : la réponse contient « partiel », « partielle »,
« incomplet » ou « incomplète », et jamais « revue complète effectuée » ni « toutes les
commandes ont été vérifiées ». Elle est appliquée *k sur n* : `JUDGE_K` réussites
(3 par défaut) sur `JUDGE_N` essais (5 par défaut).

## Exemples techniques

« Trouvez Léa Martin de Lille et donnez-moi le statut de sa commande. » → recherche du
client au cycle 0, lecture de CMD-2010 au cycle 1, puis « La commande CMD-2010 de Léa
Martin (Lille) est expédiée. »

```json
{"cycles": 3, "cycle_limit_reached": false, "interrupted": false,
 "tools": [{"name": "search_customers", "cycle": 0}, {"name": "get_order", "cycle": 1}]}
```

Événements SSE : `step` (`{"cycle": 0, "tool": "search_customers"}`), `step`, `text`, `end`.

« Faites une revue complète de toutes les commandes de Transports Morel, une par une,
en vérifiant le détail de chacune, sans vous arrêter. » → la limite est atteinte ;
événement `mention` ; « Revue partielle : j'ai vérifié 8 commandes sur 30. »

### Contre-exemples techniques

- Omettre `interrupted` dans la trace d'un tour normal.
- Enchaîner sur deux cycles deux appels indépendants : le test du groupement échoue.

## Essayer soi-même

```powershell
uv run --project workshop_kit/bootstrap workshop serve
```

Ouvrez http://127.0.0.1:8080, posez les questions du README, puis lisez la dernière ligne
de `traces/turns.jsonl`. L'interface Chainlit n'affiche ni `mention` ni `interruption` et
n'a pas de bouton d'interruption. Pour les voir, créez une conversation
(`POST http://127.0.0.1:8000/conversations`), demandez l'interruption
(`POST /conversations/{id}/interruption`), puis suivez le flux du tour suivant avec
`curl.exe -N` sur `/conversations/{id}/messages` et le corps `{"text": "..."}`.
Lancez enfin `workshop check 06`.

## Pistes techniques

- Les types d'événements et le paramètre `interrupt_requested` sont décrits dans
  `workshop_kit/shell/harness_contract.py` et `docs/interface-contract.md`.
- `workshop_kit/shell/chat_app.py` montre comment l'interface transmet l'interruption :
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

La non-régression rejoue les ateliers 03 à 06. Les tests de l'atelier 03 marqués
`superseded_by("04")` sont sautés.

```powershell
workshop start 06
workshop check 06
workshop check 06 --non-regression   # ateliers 03 à 06
```
