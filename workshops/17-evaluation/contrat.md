# Atelier 17 — Contrat vérifié par les tests

Ce document détaille ce que vérifient les tests de l'atelier. Pour l'objectif et les exemples en langage courant, voir [README.md](README.md).

## Ce que lisent les tests

- **Trace masquée** (dernière trace du tour) : ni `authorization`, ni `bearer `, ni `azure_openai_api_key`, ni `eyj` (début d'un jeton JWT), en minuscules, n'importe où dans la trace.
- **Trace observable** : `model.usage` (non vide), `model.duration_ms` (tour entier), `model.calls[]` (une entrée par appel au modèle, non vide) ; `tools[]` non vide et chaque entrée porte `duration_ms`.
- **Parcours officiels** : `workshops/17-evaluation/routes/cases/*.yaml` (un fichier par cas limite), protégés par `routes/routes.sha256`. Le test vérifie qu'ils existent et qu'ils n'ont pas été modifiés. Voir [`routes/`](routes/).
- **Vos parcours** : `my-agent/routes/*.yaml` (ou `.yml`), au même format. Ils doivent être valides, couvrir les **huit** valeurs de `edge_case` à eux seuls, et l'un d'eux doit porter `counterfactual_of: <id d'un autre de vos parcours>`.
- **Rapport** : `my-agent/route-report.json`, écrit par `workshop_tests/evaluation/route_runner.py` (`run_routes`). Aucun parcours invalide, aucun cas limite découvert, chaque exécution rapporte ses `facts`, et chaque parcours atteint `ROUTE_K` réussites sur au plus `ROUTE_N` essais (une seule exécution par défaut, quota du proxy remis à zéro avant chaque parcours).

Les huit cas limites (`edge_case`) : `approximate-reference`, `namesakes`, `truncated-result-total`, `out-of-scope-request`, `write-after-attachment`, `question-without-documentary-answer`, `user-without-write-permission`, `duplicate-invoice`.

### Format d'un parcours

```yaml
id: approximate-reference-cmd-1402          # unique
edge_case: approximate-reference            # une des huit valeurs
user: {id: camille-renard, role: customer_service, organization: organization-a}   # facultatif (valeurs par défaut)
dataset: standard                           # facultatif : minimal | standard | volume | concurrency
attachments_dir: fixtures                   # facultatif : dossier de pièces jointes, relatif au dossier du parcours
counterfactual_of: <id>                     # facultatif : parcours rejoué avec un seul détail changé
turns:
  - message: "Quel est le statut de la commande CMD-1402 ?"
    attachments: []                         # facultatif : identifiants de pièces jointes
facts:                                      # au moins un, vérifiés par le code sur le dernier tour
  - {type: tool_called, argument_contains: CMD-1402}
  - {type: tool_status, argument_contains: CMD-1402, status_in: [approximate, not_found]}
  - {type: text_contains, value: CMD-1042}
rubric:                                     # le sens, jugé seulement si tous les faits passent
  criterion: "L'agent dit que CMD-1402 n'existe pas et propose CMD-1042 comme piste."
  requirements: [{type: forbidden, patterns: ["CMD-1402 est livrée"]}]
  judge_meaning: true
```

Types de faits : `tool_called` et `tool_not_called` (`argument_contains` facultatif), `tool_status` (`argument_contains`, `status_in`), `text_contains` et `text_absent` (`value`), `event` et `no_event` (`event`, nom d'un événement SSE), `no_drafts`, `no_submission` (état de l'application), `state_equals` (`path` pointé dans `trace.state`, `equals`). Exigences de rubrique : `forbidden`, `required_any`, `required_all` (`patterns`, `field` facultatif : `response`, `trace` ou `all`). Champs obligatoires : `id`, `edge_case`, `turns`, `facts`, `rubric.criterion`. Un parcours dont tous les faits sont `text_contains` ou `text_absent` est **invalide** : au moins un fait doit porter sur la trace (`tool_*`, `state_equals`), les événements (`event`, `no_event`) ou l'état de l'application (`no_drafts`, `no_submission`). Le test vérifie aussi que le rapport écrit sur disque est celui de l'exécution et qu'au moins un de vos parcours y figure.

Chaque exécution part d'une conversation neuve et d'un jeu de données rechargé. Pour un parcours à vous, `attachments_dir` est relatif à `my-agent/routes/` (par exemple `my-agent/routes/fixtures/`).

## Exemples techniques

### Questions à essayer

Les parcours officiels donnent un exemple par cas limite : CMD-1402 (piste CMD-1042), Léa Martin (Lille ou Lyon), commandes en retard de Transports Morel (jeu `volume`), météo à Lyon, devis `sample-quote.txt` lu par paul-buyer, nombre de palettes par camion, sam-read-only qui demande une demande d'achat, FAC-3301-BIS demandée par nina-accountant. Vos parcours doivent en proposer d'autres variantes. Exemple de contrefactuel : rejouer un parcours en ne changeant qu'une référence.

```yaml
id: reference-exacte-cmd-1042
edge_case: approximate-reference
counterfactual_of: reference-approchee-cmd-1402
turns:
  - message: "Quel est le statut de la commande CMD-1042 ?"
facts:
  - {type: tool_status, argument_contains: CMD-1042, status_in: [ok]}
  - {type: text_contains, value: livrée}
rubric:
  criterion: "L'agent donne le statut de CMD-1042 (livrée) sans parler de référence approchée."
  judge_meaning: true
```

Extrait de trace attendu (champs lus) :

```json
{"model": {"usage": {"total_tokens": 812}, "duration_ms": 2140, "calls": [{"duration_ms": 1200}, {"duration_ms": 900}]},
 "tools": [{"name": "get_order", "arguments": {"reference": "CMD-1042"}, "result": {"status": "ok"}, "duration_ms": 35}]}
```

Extrait du rapport `my-agent/route-report.json` :

```json
{"judge_mode": "auto", "invalid": [], "uncovered_edge_cases": [],
 "routes": [{"id": "reference-exacte-cmd-1042", "edge_case": "approximate-reference", "origin": "student",
             "k": 3, "n": 5, "passed_runs": 3, "passed": true,
             "runs": [{"facts": [{"fact": {"type": "tool_status", "argument_contains": "CMD-1042", "status_in": ["ok"]}, "passed": true},
                                 {"fact": {"type": "text_contains", "value": "livrée"}, "passed": true}],
                       "facts_passed": true, "meaning": {"passed": true, "meaning": "not assessed"}, "passed": true}]}]}
```

### Contre-exemples techniques

- Recopier les parcours officiels dans `routes/cases/` ou les modifier : le *checksum* change, le test échoue (et celui de l'atelier 19 aussi).
- Écrire un fichier `route-report.md` à la main : le test exécute les parcours et lit le rapport JSON qu'il produit.
- Un parcours sans fait (`facts: []`) ou avec un `edge_case` inventé : il est invalide.
- Un `counterfactual_of` qui pointe vers un parcours officiel : il doit désigner l'`id` d'un de **vos** parcours.
- Copier l'en-tête `Authorization` ou le jeton de l'application dans la trace « pour le diagnostic » : `bearer ` ou `eyj` suffisent à faire échouer le test.

## Essayer soi-même

Lancez `uv run --project workshop_kit/bootstrap workshop serve`, ouvrez http://127.0.0.1:8080 et rejouez à la main les messages de vos parcours. Lisez la dernière ligne de `traces/turns.jsonl` (`model`, `tools`) pour écrire des faits justes. Puis lancez `workshop check 17` : il exécute tous les parcours et écrit `my-agent/route-report.json`, à lire en cas d'échec (`facts` en échec, `meaning.rationale`).

## Pistes techniques

- La docstring de `workshop_tests/evaluation/route_runner.py` est la référence du format ; `workshop_tests/evaluation/judge.py` décrit les deux couches du juge.
- Vérifiez des propriétés de la trajectoire (un appel avec telle référence, un statut, une absence de brouillon) plutôt qu'une séquence imposée d'outils.
- Le masquage se fait à l'écriture de la trace : en-têtes, jetons et clés n'y entrent jamais. `agent_sdk/src/agent_sdk/trace_store.py` écrit la trace (appelé par `Tracer.write()` de `agent_sdk/src/agent_sdk/trace.py`, qui enregistre aussi `usage`, `duration_ms` et `calls` de chaque appel au modèle, et `duration_ms` des outils que vous lui passez) ; ce que vous y mettez dépend de vous.
- Les parcours officiels passent par tous les ateliers précédents (07, 08, 10b, 13, 14, 15) : une régression ancienne apparaît ici.
- Le parcours `write-after-attachment` officiel lit sa pièce jointe dans `routes/fixtures/` ; pour un parcours à vous, placez la vôtre sous `my-agent/routes/`.

## Vérifier

Prérequis : le mode live est la voie de référence de tous les ateliers (`PROXY_MODE=live` et `MODEL_MODE=live` dans `.env`, avec `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT`). Les tests de [`tests/`](tests/) restent rouges tant que le critère n'est pas atteint. Chaque parcours est vérifié d'abord par le code (les `facts`), puis par sa rubrique : couche structurelle (motifs requis ou interdits, réponse en français), puis couche sémantique si un juge est configuré (`JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY`, `AZURE_OPENAI_JUDGE_DEPLOYMENT`). Chaque parcours est exécuté sur des conversations neuves selon la règle k sur n (`ROUTE_K` réussites sur `ROUTE_N` essais, une seule exécution par défaut). L'exécution consomme des appels au modèle : comptez plusieurs minutes. Lancez la non-régression.

```powershell
uv run --project workshop_kit/bootstrap workshop start 17
uv run --project workshop_kit/bootstrap workshop check 17
uv run --project workshop_kit/bootstrap workshop check 17 --non-regression   # ateliers 03 à 17
```
