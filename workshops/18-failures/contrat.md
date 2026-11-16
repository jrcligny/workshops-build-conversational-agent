# Atelier 18 — Contrat vérifié par les tests

Ce document détaille ce que vérifient les tests de l'atelier. Pour l'objectif et les exemples en langage courant, voir [README.md](README.md).

## Ce que lisent les tests

- **Panne du modèle** : le test arme `POST {proxy}/_test/failures` avec `{"type": "primary_model", "active": true}`. Le proxy répond alors 503 à tout appel dont le `model` demandé ne contient pas `fallback` ; un `model` qui contient `fallback` reste joignable.
- **Journal du proxy** (`GET /log`, entrées `route`, `model`, `code`) : exactement **un** appel en 503 au modèle principal, puis au moins un appel dont le `model` contient `fallback`, tous en 200.
- **Trace `fallback`** : objet `{from, to, reason}`, `to` non vide. La réponse contient « livrée » (statut de CMD-1042).
- **Panne de l'application** : le test arme `unknown_outcome` (`POST /observation/failures` de l'API métier). `POST /drafts/{id}/submit` répond alors **504** sans rien écrire.
- **Journal de l'API métier** (`method`, `route`, `code`) : exactement **une** tentative `POST …/submit`, de code 504 ; toujours une seule après le tour suivant, où l'utilisateur insiste (« Elle n'est sans doute pas partie : réessayez la soumission. ») sans refaire le geste de confirmation.
- **Trace `unknown_outcome`** : objet `{draft_id}`, égal au `draft_id` porté par l'événement SSE `confirmation_requested` (atelier 10b). `submitted_requests` reste vide.
- **Trace `versions`** : objet avec `instructions`, `tools`, `skills` et `index`, chacun non vide. Deux tours de suite donnent les mêmes versions ; après une reconstruction de l'index documentaire incluant la version retirée de la procédure (`POST /indexing/rebuild` `{"include_retired": true}`, faite par le test puis annulée), `versions.index` change et les autres composants non. La version de l'index se lit donc sur l'index en service (par exemple `GET /indexing/state`), à chaque tour.
- **Utilisateurs** : `paul-buyer` (`buyer`) pour la soumission, `camille-renard` pour les lectures.
- **Rubriques** (règle k sur n) : pour l'issue inconnue, la réponse contient « vérifi » ou « contrôl » et aucun de « a bien été soumise », « a été soumise avec succès », « j'ai soumis », « a échoué » ; le scénario entier est rejoué sur des conversations neuves jusqu'à `JUDGE_K` réussites sur `JUDGE_N`. Pour le repli, la réponse contient « secours », « repli » ou « modèle de remplacement » (jugée une fois).

Restent libres : le format des numéros de version (date, empreinte, numéro), la valeur de `reason`, la formulation des messages.

## Exemples techniques

### Questions à essayer

| Situation | Message | Comportement attendu |
|---|---|---|
| Modèle principal en panne | « Quel est le statut de la commande CMD-1042 de Martin Durand ? » | Un 503, une bascule, « CMD-1042 est livrée (réponse produite par le modèle de secours) » |
| Soumission à l'issue inconnue | « Préparez une demande d'achat pour des ramettes de papier, 120 euros. », geste de confirmation, puis « Je confirme la soumission de cette demande. » | Une seule tentative (504), « Je ne sais pas si votre demande a été enregistrée ; vérifiez dans l'application avant de recommencer. » |
| Tour ordinaire | « Quel est le statut de la commande CMD-1042 ? » | Trace avec `versions` complet |

Extraits de trace attendus :

```json
{"fallback": {"from": "default", "to": "fallback", "reason": "503 primary model unavailable"},
 "versions": {"instructions": "2026-03-01", "tools": "v3", "skills": "catalog-1.2", "index": "a41f9c"}}
```

```json
{"unknown_outcome": {"draft_id": "DRAFT-3f2a9c1b7e"}}
```

Journal du proxy attendu pendant la panne :

```json
[{"route": "/v1/chat/completions", "model": "default", "code": 503},
 {"route": "/v1/chat/completions", "model": "…fallback…", "code": 200}]
```

### Contre-exemples techniques

- Réessayer le modèle principal avant de basculer : deux entrées en 503, le test échoue.
- Rejouer la soumission après le 504, « pour être sûr » : deux tentatives dans le journal de l'API métier.
- Répondre « votre demande a échoué » ou « a bien été soumise » : l'issue est inconnue, la rubrique l'interdit.
- Afficher une erreur générique sans réponse : le tour doit se terminer (`text` puis `end`) et dire ce qui a été fait.
- Écrire `"versions": {"tools": ""}` ou omettre `index` : chaque composant doit nommer sa version.

## Essayer soi-même

Lancez `uv run --project workshop_kit/bootstrap workshop serve`. Armez la panne du modèle, posez la question dans l'interface (http://127.0.0.1:8080), puis désarmez-la :

```powershell
Invoke-RestMethod -Method Post http://127.0.0.1:8003/_test/failures -ContentType application/json -Body '{"type":"primary_model","active":true}'
Invoke-RestMethod -Method Post http://127.0.0.1:8003/_test/failures -ContentType application/json -Body '{"type":"primary_model","active":false}'
```

Pour l'issue inconnue, armez `{"type":"unknown_outcome","active":true}` sur `POST http://127.0.0.1:8001/observation/failures` avec l'en-tête `Authorization: Bearer <OBSERVATION_TOKEN>`. L'interface de chat ne gère pas le geste de confirmation : envoyez-le par `POST http://127.0.0.1:8000/conversations/{id}/confirmation` `{"confirmed": true}`. Lisez la dernière ligne de `traces/turns.jsonl` (`fallback`, `unknown_outcome`, `versions`), puis lancez `workshop check 18`.

## Pistes techniques

- `workshop_kit/llm_proxy/app.py` montre la panne simulée ; `workshop_kit/llm_proxy/live.py` (`ROLE_SETTINGS`) associe le nom logique `fallback` à `AZURE_OPENAI_FALLBACK_DEPLOYMENT`. `ModelClient.generate(..., model="fallback")` (`workshop_kit/shell/model_client.py`) sollicite le modèle de repli ; une panne (5xx, 429, délai, service injoignable) y lève `ModelUnavailable`, quelle que soit la bibliothèque HTTP sous-jacente (`model_unavailable(exc)` classe une exception levée par votre propre client). Le choix de basculer relève de votre *harness*. Ces trois noms sont aussi exposés par `my-agent/agent_helpers/kit.py` (`model_client()`, `ModelUnavailable`, `model_unavailable`).
- Distinguez le sort de la requête : un 503 du modèle n'a rien écrit ; un 504 sur `/submit` a peut-être écrit. Les lectures peuvent être réessayées, `/submit` jamais.
- La soumission vient de l'atelier 10b : `confirmation_requested` porte `draft_id`, et le tour suivant reçoit `confirmation=True`.
- Les versions se lisent là où vous les tenez : consignes, définitions d'outils, `my-agent/skills/manifest.yaml` (atelier 14), index documentaire (atelier 13).
- Un tour interrompu se termine par un signal explicite et un message qui dit ce qui a été fait et ce qui ne l'a pas été.

## Vérifier

Prérequis : le mode live est la voie de référence (`PROXY_MODE=live` et `MODEL_MODE=live` dans `.env`, avec `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT` et, pour cet atelier, `AZURE_OPENAI_FALLBACK_DEPLOYMENT`). Les tests de [`tests/`](tests/) restent rouges tant que le critère n'est pas atteint. Ils vérifient d'abord par le code les journaux du proxy et de l'API métier, l'état de l'application et la trace, puis le sens par une rubrique : couche structurelle, puis juge sémantique si configuré (`JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY`, `AZURE_OPENAI_JUDGE_DEPLOYMENT`). La rubrique de l'issue inconnue est répétée selon la règle k sur n (`JUDGE_K` sur `JUDGE_N`). Lancez la non-régression : elle rejoue notamment les parcours de l'atelier 17 avec votre *harness* modifié.

```powershell
uv run --project workshop_kit/bootstrap workshop start 18
uv run --project workshop_kit/bootstrap workshop check 18
uv run --project workshop_kit/bootstrap workshop check 18 --non-regression   # ateliers 03 à 18
```
