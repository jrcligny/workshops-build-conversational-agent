# Atelier 07 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.

## Ce que lisent les tests

Sont imposés dans la trace :

- `tools[].result.orders` (liste), `tools[].result.total` (total exact) et
  `tools[].result.truncated` (booléen) pour une liste bornée ;
- `tools[].arguments.mode == "count"` et `tools[].result.count` en mode décompte, sans
  liste `orders` ;
- `model.calls[].context_size`, renseigné pour chaque appel au modèle ;
- `compaction`, un objet présent seulement sur le tour qui compacte, avec
  `summarized_answers` (au moins 1), `kept_user_messages` (au moins 1 : les messages
  utilisateur anciens gardés mot pour mot) et `threshold` (le seuil réglé) ; la clé est
  absente sous le seuil.

Dans le flux SSE, le tour qui compacte émet un événement `compaction` ou `mention`.

Les tests vérifient aussi :

- jeu `volume`, liste des retards de Transports Morel : moins de 60 lignes,
  `truncated` vrai, `total` à 60, et « 60 » dans la réponse ;
- décompte : `count` à 60, aucune ligne, et « 60 » dans la réponse ;
- sous le seuil : la demande initiale est rejouée telle quelle dans l'historique, et la
  trace ne contient pas de clé `compaction` ;
- au-delà du seuil (`COMPACTION_MESSAGE_THRESHOLD`, 8 par défaut) : chaque message
  précédent de l'utilisateur figure mot pour mot dans `input.history` (rôle `user`),
  `input.message` est le message courant, et l'historique est plus court que la
  conversation complète (moins de réponses `assistant` que de tours précédents).

Restent libres : la limite d'affichage, le contenu et la forme du résumé, le moment exact
de la compaction et la mesure de taille utilisée.

Rubrique `07-partial-result-announced` : la réponse contient « partiel », « partielle »,
« une partie », « extrait » ou « premières ». Elle est appliquée une seule fois, pas en
*k sur n*.

## Exemples techniques

« Quelles sont les commandes en retard de Transports Morel ? » (jeu `volume`) → « Voici
les 20 premières sur 60 commandes en retard. »

```json
{"name": "list_customer_orders", "arguments": {"customer_id": "C-VOLUMEX", "filter": "late"},
 "result": {"status": "ok", "orders": ["…20 lignes…"], "total": 60, "truncated": true}}
```

« Combien de commandes en retard a Transports Morel ? Je veux seulement le nombre, pas
les lignes. » → « 60 commandes en retard. »

```json
{"arguments": {"customer_id": "C-VOLUMEX", "filter": "late", "mode": "count"},
 "result": {"status": "ok", "count": 60}}
```

« Je traite le dossier de Martin Durand, commande CMD-1042, commandes livrées
uniquement. » suivi de dix messages « Détail numéro 1 : je veux seulement les commandes
livrées de CMD-1042. »… → sur le tour qui compacte, la trace contient
`{"compaction": {"summarized_answers": 4, "kept_user_messages": 10, "threshold": 8}}`
et le flux émet `{"type": "compaction", ...}`.

## Essayer soi-même

```powershell
uv run --project workshop_kit/bootstrap workshop serve
```

Ouvrez http://127.0.0.1:8080, posez les questions du README, puis lisez la dernière ligne
de `traces/turns.jsonl`. L'interface Chainlit n'affiche ni `compaction` ni `mention` :
suivez le flux avec `curl.exe -N` sur
`http://127.0.0.1:8000/conversations/{id}/messages` (corps `{"text": "..."}`).
Lancez enfin `workshop check 07`.

## Pistes techniques

- `GET /customers/{id}/orders` accepte `filter` et `limit`, et renvoie `orders`, `total`,
  `truncated` et `limit` (voir `workshop_kit/apps/business_api/app.py`).
- Le seuil se lit dans `workshop_kit/shell/config.py` et `.env.example`
  (`COMPACTION_MESSAGE_THRESHOLD`).
- Mesurez `context_size` juste avant chaque appel au modèle, et enregistrez-le avec
  `workshop_kit/shell/tracer.py`.
- La compaction porte sur ce que vous envoyez au modèle ; le *harness* reçoit
  l'historique complet de l'interface à chaque tour.
- Les assertions détaillées sont dans [tests/](tests/).

## Vérifier

Le mode live est nécessaire : `PROXY_MODE=live`, `MODEL_MODE=live`,
`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Les tests restent rouges tant que le critère n'est pas atteint. Les contrôles de code
passent d'abord, puis la rubrique. Le juge utilise `JUDGE_MODE`, `JUDGE_BASE_URL`,
`JUDGE_API_KEY` et `AZURE_OPENAI_JUDGE_DEPLOYMENT` pour sa couche de sens. Les
rubriques des ateliers précédents sont répétées *k sur n*.

La non-régression rejoue les ateliers 03 à 07. Les tests de l'atelier 03 marqués
`superseded_by("04")` sont sautés.

```powershell
workshop start 07
workshop check 07
workshop check 07 --non-regression   # ateliers 03 à 07
```
