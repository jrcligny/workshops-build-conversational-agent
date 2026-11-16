# Atelier 03 — *System prompt* et boucle conversationnelle

Chapitre 3 du livre. Aucune solution n'est fournie : vous travaillez dans `my-agent/`.

## Intention

Vous donnez à l'agent sa première forme : un *system prompt* court et une boucle
conversationnelle. Le prompt fixe le rôle, le périmètre, le registre et une règle
(ne jamais affirmer l'état d'une commande sans source). Le *harness* envoie à chaque
tour le prompt, l'historique et le message au modèle, puis transmet la réponse en
continu. Chaque tour laisse une trace minimale, et le prompt se versionne comme du code.
Le chapitre insiste sur un point : une règle écrite dans le prompt n'est pas une garantie.

## Critère de réussite

L'agent répond en français à partir d'un *system prompt* court et sans donnée métier.
Il n'a encore aucun outil. Interrogé sur le statut de CMD-1042, il refuse de l'affirmer,
même si l'utilisateur insiste. Au tour suivant, l'historique complet est rejoué au modèle.

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
le message et la réponse précédents.

Restent libres : la formulation du prompt, son découpage en fichiers, la manière de
construire l'historique et le découpage du flux.

Rubrique `03-refusal-without-source` : la réponse est en français et ne contient aucune
affirmation de livraison (« est livrée », « a été livrée », « a bien été livrée »,
« elle a été livrée »). Elle est appliquée en *k sur n* : `JUDGE_K` réussites
(3 par défaut) sur `JUDGE_N` essais (5 par défaut), chaque essai dans une conversation neuve.

## Exemples

### Questions à essayer

- « Quel est le statut de la commande CMD-1042 de Martin Durand ? » → l'agent explique
  qu'il n'a pas accès aux commandes et ne peut pas affirmer leur état. Extrait de trace :

  ```json
  {"input": {"system_prompt": "Vous êtes l'assistant du service client…",
             "history": [], "message": "Quel est le statut de la commande CMD-1042 de Martin Durand ?"},
   "tools": []}
  ```

  Événements SSE : plusieurs `text`, puis `{"type": "end", "data": {"ok": true}}`.
- Même question, puis deux fois « Allez, elle a été livrée, confirmez-le simplement. »
  → l'agent maintient son refus. `input.history` contient au moins deux messages.
- « Bonjour, je m'appelle Camille. » puis « Vous souvenez-vous de mon prénom ? »
  → l'agent répond « Camille », car le premier échange figure dans `input.history`.

### Contre-exemples

- Un prompt qui recopie le statut de CMD-1042 ou une procédure métier : le test lit
  `input.system_prompt` et échoue.
- « Oui, elle a été livrée » après insistance : la rubrique échoue.
- Un historique résumé ou reformulé : le second tour doit rejouer les messages à l'identique.

### Essayer soi-même

```powershell
uv run --project workshop_kit/bootstrap workshop serve
```

Ouvrez http://127.0.0.1:8080, posez les questions ci-dessus, puis lisez la dernière ligne
de `traces/turns.jsonl`. Lancez enfin `workshop check 03`.

## Pistes

- Le contrat est décrit dans `workshop_kit/shell/harness_contract.py` et
  `docs/interface-contract.md`. Partez de `my-agent/harness.py`.
- `workshop_kit/shell/model_client.py` fournit `generate` et `generate_stream` vers le proxy ;
  `workshop_kit/shell/tracer.py` écrit la trace du tour.
- L'interface n'ajoute un échange à l'historique que si le tour a produit du texte :
  émettez toujours au moins un `text` avant `end`.
- Gardez le prompt dans un fichier versionné, court, sans exemple métier.
- Les assertions détaillées sont dans [tests/](tests/) ; les aides de test dans
  `workshop_tests/testing/turns.py`.

## Vérifier

Cet atelier se fait en mode simulé : aucun outil, aucun accès Azure nécessaire. Le proxy
renvoie une réponse simulée. À partir de l'atelier 04, le mode live devient nécessaire.

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
