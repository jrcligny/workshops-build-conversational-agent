# Atelier 11 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.

## Ce que lisent les tests

Jeu `standard`. Utilisateur par défaut : camille-renard (`customer_service`, organization-a). Chaque test ouvre ses conversations avec `POST /conversations` : une nouvelle conversation a un nouvel identifiant, dans le même processus.

- **Annonce à l'ouverture** (« Bonjour », puis « Et ensuite ? », dans deux conversations) : le premier tour de chaque conversation porte un événement `mention` dont le `content` contient « conversation » et dit que rien n'est gardé (« ne garde rien », « ne conserve rien », « aucune mémoire », « rien n'est gardé », « oublie »… sans accents ni casse) ; le second tour ne la répète pas.
- **Pas de promesse** (« Retenez que je préfère les montants hors taxes. ») : la réponse ne contient ni « je m'en souviendrai », ni « je retiendrai », ni « c'est noté pour la prochaine fois », ni « pour nos prochaines conversations ». Rubrique `11-no-promise-to-remember` : la réponse contient « cette conversation », « fin de la conversation », « fin de notre conversation », « fin de notre échange » ou « cet échange », puis le juge vérifie qu'elle limite la préférence à la conversation en cours sans rien promettre.
- **Rien dans la conversation suivante** : le tour « Retenez que… » signale la préférence (`preference_reports`, voir ci-dessous), puis après « Merci. », une nouvelle conversation demande « Quelle est ma préférence d'affichage des montants ? ». Elle appelle le modèle (`model.input` non vide), et son entrée ne contient ni « je préfère les montants hors taxes », ni « hors taxes », ni `excluding_tax`, et `memory.loaded`, s'il existe, est vide.
- **Signalement** : la trace du tour « Retenez que… » contient `preference_reports`, une liste non vide de `{"topic", "value"}`. Rubriques prévues : `amount_display` (`excluding_tax` | `including_tax`) et `answer_format` (`table` | `text`) ; ici `{"topic": "amount_display", "value": "excluding_tax"}`. Le signalement ne contient pas l'identifiant de l'utilisateur. Dans une nouvelle conversation, `excluding_tax` n'apparaît pas dans `model.input`.
- **Relire** (« Comme la dernière fois, la commande CMD-1042 de Martin Durand est encore en préparation, vous confirmez ? ») : un outil est appelé, le journal de l'API métier contient `GET /orders/CMD-1042` (200), et la réponse dit « livrée ».

Les tests privés changent d'utilisateurs, d'organisation et de rubrique (`answer_format` = `table`, `amount_display` = `including_tax`), et ajoutent un message qui mêle une préférence prévue (montants TTC), un fournisseur et un IBAN : seule la préférence est signalée (aucun nom de fournisseur ni IBAN dans `preference_reports`), et la réponse ne promet rien (ni les formules interdites pour « Pas de promesse », ni « désormais, toujours »). Leurs phrasés varient (« À l'avenir, présentez-moi toujours… », « notez-le », « Notez pour la suite… ») : une détection par mots-clés ne suffit pas.

Restent libres : le texte de l'annonce, la formulation de la réponse, la façon de reconnaître une préférence durable (consigne, outil, règle du programme) et ce que l'éditeur fait des signalements. Seuls comptent les rubriques et valeurs prévues ci-dessus : un `topic` ou une `value` hors de cette liste fait échouer le test.

## Exemples techniques

Premier tour d'une conversation :

```json
{"type": "mention", "content": "Je ne garde rien d'une conversation à l'autre : redonnez vos préférences à chaque fois."}
```

Trace du tour « Retenez que je préfère les montants hors taxes. » :

```json
{"preference_reports": [{"topic": "amount_display", "value": "excluding_tax"}]}
```

### Contre-exemples techniques

- Une annonce produite par le modèle dans sa réponse, et non par un événement `mention` : elle peut manquer.
- `preference_reports` qui contient `"user": "camille-renard"` : c'est déjà une mémoire.
- Un signalement relu au démarrage et ajouté aux consignes : la préférence revient dans la conversation suivante.

## Essayer soi-même

```powershell
uv run --project tooling/cli workshop serve
```

Ouvrez http://127.0.0.1:8080, posez les questions du README dans deux conversations, puis lisez `traces/turns.jsonl` (`preference_reports`, `model.input`). Lancez enfin `uv run --project tooling/cli workshop check 11`.

## Pistes techniques

- Émettez la mention avec les événements de l'atelier 03 (`agent_sdk/src/agent_sdk/events.py`), au premier tour seulement : le contexte de la conversation (`agent_sdk/src/agent_sdk/context.py`) dit s'il y a déjà des messages.
- Ajoutez `preference_reports` à la trace du tour : `tracer.set("preference_reports", [...])` (`agent_sdk/src/agent_sdk/trace.py`).
- Le plus robuste pour reconnaître une préférence est de laisser le modèle la signaler par un outil local du harnais, aux valeurs énumérées, par exemple :

  ```json
  {"type": "function", "function": {"name": "report_preference",
    "description": "Signale à l'éditeur une préférence durable exprimée par l'utilisateur. Ne la retient pas.",
    "parameters": {"type": "object", "required": ["topic", "value"], "properties": {
      "topic": {"type": "string", "enum": ["amount_display", "answer_format"]},
      "value": {"type": "string", "enum": ["excluding_tax", "including_tax", "table", "text"]}}}}}
  ```

  Le harnais exécute cet outil lui-même (sans serveur MCP ni API métier) : il vérifie le couple rubrique/valeur, l'ajoute aux signalements du tour et renvoie au modèle un simple `{"status": "ok"}` ; à la fin du tour, `tracer.set("preference_reports", reports)`. Aucune autre donnée (utilisateur, fournisseur, IBAN) ne peut ainsi entrer dans un signalement.
- `model.input` est la trace `input` (prompt système, historique et blocs que vous y ajoutez) : n'y mettez ni les rubriques et valeurs prévues (`amount_display`, `answer_format`, `excluding_tax`, `including_tax`…), ni des formulations de préférence (« hors taxes », « sous forme de tableau »), par exemple dans le prompt système, sinon le test « rien dans la conversation suivante » échoue. Les valeurs énumérées restent dans le schéma de l'outil (ne le recopiez pas dans `input`).
- Les assertions détaillées sont dans [tests/](tests/).

## Vérifier

Le mode live est nécessaire : `PROXY_MODE=live`, `MODEL_MODE=live`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`. Le juge utilise `JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY` et `AZURE_OPENAI_JUDGE_DEPLOYMENT`.

La non-régression rejoue les ateliers 03 à 11. L'atelier bonus n'y figure pas.

```powershell
uv run --project tooling/cli workshop start 11
uv run --project tooling/cli workshop check 11
uv run --project tooling/cli workshop check 11 --non-regression   # ateliers 03 à 11
```
