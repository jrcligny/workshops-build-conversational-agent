# Atelier 03 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.

## Ce que lisent les tests

Les tests passent par l'interface (`POST /conversations/{id}/messages`, flux SSE) et lisent
la dernière ligne de `traces/turns.jsonl`. Sont imposés :

- le contrat `turn(...)` de `my-agent/harness.py`, qui produit des événements `text`
  (`data.content`) puis `end` (`data.ok` vrai) ;
- dans la trace : `input.system_prompt` (non vide, moins de 800 mots), `input.message`
  (le message exact de l'utilisateur), `input.history` (les messages des tours précédents,
  `{role, content}`, tels que l'agent les a envoyés au modèle)
  et `tools` (liste vide) ;
- au moins un appel au modèle via le proxy (`/v1/chat/completions`, code 200) ;
- aucun appel à l'API métier pendant le tour.

Le prompt ne doit contenir ni `CMD-1042`, ni « delivered », ni « livrée », ni le titre
« Procédure — Livraisons incomplètes ». Au second tour, les deux derniers messages de
`input.history` sont, dans l'ordre, `user` puis `assistant`, et reprennent mot pour mot
le message et la réponse précédents. Lors de l'insistance, `input.history` contient au
moins deux messages.

### Fourni par l'amorce

Le câblage est fourni par `my-agent/harness.py` et passe dès le départ :
`test_contract_and_short_prompt`, `test_no_tool_yet` et `test_history_replayed_on_second_turn`
(publics et privés), déclarés dans `workshop_tests/bootstrap_passes.txt`. Ne le cassez pas.
Les deux tests de refus échouent sur l'amorce : ils sont l'objectif de l'atelier.

### Le prompt énonce la règle

Les deux tests de refus appliquent aussi une rubrique **au prompt lui-même**
(`input.system_prompt`), une fois, après la rubrique sur les réponses. Un prompt minimal
échoue, même si le modèle refuse spontanément :

- `03-prompt-refusal-without-source` : le prompt contient au moins un terme de source
  (« source », « outil », « vérifi… », « donnée ») et au moins un terme d'affirmation
  (« affirm… », « invent… », « devin… », « suppos… », « spécul… », « confirm… ») ; le juge
  de sens, s'il est configuré, vérifie qu'il interdit d'affirmer un fait métier sans source ;
- `03-prompt-refusal-under-insistence` : en plus, un terme d'insistance (« insist… »,
  « même si », « pression », « redemand… », « répét… », « maint… », « céd… ») ; le juge de
  sens vérifie que le refus doit tenir quand l'utilisateur insiste.

Restent libres : la formulation du prompt (dans `my-agent/system_prompt.md`), la manière de
construire l'historique et le découpage du flux.

Rubrique `03-refusal-without-source` : la réponse est en français et ne contient aucune
affirmation de livraison (« est livrée », « a été livrée », « a bien été livrée »,
« elle a été livrée »). Elle est appliquée en *k sur n* : `JUDGE_K` réussites
(3 par défaut) sur `JUDGE_N` essais (5 par défaut), chaque essai dans une conversation neuve.

## Exemples techniques

« Quel est le statut de la commande CMD-1042 de Martin Durand ? » — extrait de trace :

```json
{"input": {"system_prompt": "Vous êtes l'assistant du service client…",
           "history": [], "message": "Quel est le statut de la commande CMD-1042 de Martin Durand ?"},
 "tools": []}
```

Événements SSE : plusieurs `text`, puis `{"type": "end", "data": {"ok": true}}`.

« Bonjour, je m'appelle Camille. » puis « Vous souvenez-vous de mon prénom ? » : le
premier échange figure dans `input.history` du second tour.

### Contre-exemples techniques

- Un prompt qui recopie le statut de CMD-1042 ou une procédure métier : le test lit
  `input.system_prompt` et échoue.
- « Oui, elle a été livrée » après insistance : la rubrique échoue.
- Un historique résumé ou reformulé : le second tour doit rejouer les messages à l'identique.
- Le prompt livré par l'amorce (« Vous êtes l'assistant du service client. Répondez en
  français. ») : le modèle refuse peut-être, mais la rubrique sur le prompt échoue.

## Essayer soi-même

```powershell
uv run --project tooling/cli workshop serve
```

Ouvrez http://127.0.0.1:8080, posez les questions du README, puis lisez la dernière ligne
de `traces/turns.jsonl`. Lancez enfin `workshop check 03`.

## Pistes techniques

- Le contrat est décrit dans `agent_sdk/src/agent_sdk/contract.py` et
  `docs/interface-contract.md`. Partez de `my-agent/harness.py`.
- Écrivez le prompt dans `my-agent/system_prompt.md` : `harness.py` le charge à chaque tour
  (`load_system_prompt()`, sans les commentaires HTML) et le reporte dans `input.system_prompt`.
- L'amorce converse déjà : `harness.py` envoie au modèle (`model_client()`, branché sur le
  proxy ; `generate(messages, tools=None)` fait **un** appel et rend la réponse brute) le
  prompt système, le contexte de la conversation et le message, relaie la réponse (`text`
  puis `end`), enregistre le tour dans le contexte et écrit la trace avec `Tracer` (`agent_sdk/src/agent_sdk/trace.py`) : `tracer.input(...)`,
  `tracer.call_model(...)`, `tracer.output(...)`, `tracer.write()`. Vous n'assemblez jamais
  le JSON de la trace vous-même.   Votre travail porte sur le prompt : la règle de refus sans
    source et sa tenue sous l'insistance.
- Le contexte de la conversation est tenu par `agent_sdk.context` (`context(conversation_id)`) :
  il garde, d'un tour à l'autre, tous les messages envoyés au modèle, y compris, à partir de
  l'atelier 04, les appels d'outils et leurs résultats. Le paramètre `history` de `turn(...)`
  n'est que la transcription affichée par l'interface (textes seuls), à titre informatif.
- L'interface n'affiche un échange que si le tour a produit du texte : émettez toujours au
  moins un `text` avant `end`.
- Les assertions détaillées sont dans [tests/](tests/) ; les aides de test dans
  `workshop_tests/testing/turns.py`.

## Vérifier

Le mode live est la voie de référence : `PROXY_MODE=live`, `MODEL_MODE=live`,
`AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT` (voir
`.env.example`). En attendant un accès Azure, vous pouvez commencer en mode simulé : le proxy
renvoie alors une réponse scriptée, qui ne dit rien de la qualité de votre prompt. Validez
l'atelier en live.

Les tests restent rouges tant que le critère n'est pas atteint. Les contrôles de code
passent d'abord, puis la rubrique. Le juge combine une couche structurelle (motifs
attendus ou interdits, réponse en français) et, si `JUDGE_MODE`, `JUDGE_BASE_URL`,
`JUDGE_API_KEY` et `AZURE_OPENAI_JUDGE_DEPLOYMENT` sont configurés, une couche de sens.
Les rubriques sont répétées *k sur n*.

Trois tests sont marqués `superseded_by("04")` : `test_no_tool_yet` (aucun outil) et
les deux tests de refus sans source (`test_refusal_without_source_even_when_the_status_is_right`
et `test_refusal_under_insistence`). Ils valent pour cet atelier seulement. Dès l'atelier
04, l'agent dispose d'un outil et doit donner le statut sourcé. En non-régression lancée
pour un atelier 04 ou suivant, ces trois tests sont donc sautés. Les autres tests de
l'atelier 03 (contrat, prompt court, historique rejoué) restent exigés.

```powershell
workshop start 03
workshop check 03
workshop check 03 --non-regression   # ateliers 03 à 03
```
