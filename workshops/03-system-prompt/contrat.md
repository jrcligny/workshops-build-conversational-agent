# Atelier 03 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.

## Ce que lisent les tests

Les tests passent par l'interface (`POST /conversations/{id}/messages`, flux SSE) et lisent
la dernière ligne de `traces/turns.jsonl`. Sont imposés :

- le contrat `turn(...)` de `my-agent/harness.py`, qui produit des événements `text`
  (`data.content`) puis `end` (`data.ok` vrai) ;
- dans la trace : `input.system_prompt` (non vide, moins de 800 mots), `input.message`
  (le message exact de l'utilisateur), `input.history` (liste de `{role, content}`)
  et `tools` (liste vide) ;
- au moins un appel au modèle via le proxy (`/v1/chat/completions`, code 200) ;
- aucun appel à l'API métier pendant le tour.

Le prompt ne doit contenir ni `CMD-1042`, ni « delivered », ni « livrée », ni le titre
« Procédure — Livraisons incomplètes ». Au second tour, les deux derniers messages de
`input.history` sont, dans l'ordre, `user` puis `assistant`, et reprennent mot pour mot
le message et la réponse précédents. Lors de l'insistance, `input.history` contient au
moins deux messages.

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

## Essayer soi-même

```powershell
uv run --project workshop_kit/bootstrap workshop serve
```

Ouvrez http://127.0.0.1:8080, posez les questions du README, puis lisez la dernière ligne
de `traces/turns.jsonl`. Lancez enfin `workshop check 03`.

## Pistes techniques

- Le contrat est décrit dans `workshop_kit/shell/harness_contract.py` et
  `docs/interface-contract.md`. Partez de `my-agent/harness.py`.
- Écrivez le prompt dans `my-agent/system_prompt.md` : `harness.py` le charge à chaque tour
  (`load_system_prompt()`, sans les commentaires HTML) et le reporte dans `input.system_prompt`.
- L'amorce converse déjà : `harness.py` envoie au modèle (`model_client()`, branché sur le
  proxy ; `generate(messages, tools=None)` fait **un** appel et rend la réponse brute) le
  prompt système, l'historique et le message, relaie la réponse (`text` puis `end`) et écrit
  la trace avec `Tracer` (`my-agent/agent_helpers/trace.py`) : `tracer.input(...)`,
  `tracer.call_model(...)`, `tracer.output(...)`, `tracer.write()`. Vous n'assemblez jamais
  le JSON de la trace vous-même. Votre travail porte sur le prompt et sur ce que l'agent dit
  quand il n'a pas de source.
- L'interface n'ajoute un échange à l'historique que si le tour a produit du texte :
  émettez toujours au moins un `text` avant `end`.
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
