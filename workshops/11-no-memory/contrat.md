# Atelier 11 — Contrat vérifié par les tests

Ce document complète le [README.md](README.md) : il détaille ce que lisent les tests et comment vérifier l'atelier.

## Ce que lisent les tests

Jeu `standard`. Utilisateur par défaut : camille-renard (`customer_service`, organization-a). Chaque test ouvre ses conversations avec `POST /conversations` : une nouvelle conversation a un nouvel identifiant, dans le même processus.

- **Annonce à l'ouverture** (« Bonjour », puis « Et ensuite ? », dans deux conversations) : le premier tour de chaque conversation porte un événement `mention` dont le `content` contient « conversation » et dit que rien n'est gardé (« ne garde rien », « ne conserve rien », « aucune mémoire », « rien n'est gardé », « oublie »… sans accents ni casse) ; le second tour ne la répète pas.
- **Pas de promesse** (« Retenez que je préfère les montants hors taxes. ») : la réponse ne contient ni « je m'en souviendrai », ni « je retiendrai », ni « c'est noté pour la prochaine fois », ni « pour nos prochaines conversations ». Rubrique `11-no-promise-to-remember` : la réponse contient « cette conversation », « fin de la conversation », « fin de notre conversation », « fin de notre échange » ou « cet échange », puis le juge vérifie qu'elle limite la préférence à la conversation en cours sans rien promettre.
- **Rien dans la conversation suivante** : après « Retenez que… » et « Merci. », une nouvelle conversation demande « Quelle est ma préférence d'affichage des montants ? ». L'entrée du modèle (`model.input`) ne contient ni « je préfère les montants hors taxes », ni « hors taxes », ni `excluding_tax`, et `memory.loaded`, s'il existe, est vide.
- **Signalement** : la trace du tour « Retenez que… » contient `preference_reports`, une liste non vide de `{"topic", "value"}`. Rubriques prévues : `amount_display` (`excluding_tax` | `including_tax`) et `answer_format` (`table` | `text`) ; ici `{"topic": "amount_display", "value": "excluding_tax"}`. Le signalement ne contient pas l'identifiant de l'utilisateur. Dans une nouvelle conversation, `excluding_tax` n'apparaît pas dans `model.input`.
- **Relire** (« Comme la dernière fois, la commande CMD-1042 de Martin Durand est encore en préparation, vous confirmez ? ») : un outil est appelé, le journal de l'API métier contient `GET /orders/CMD-1042` (200), et la réponse dit « livrée ».

Les tests privés changent d'utilisateurs, d'organisation et de rubrique (`answer_format` = `table`, `amount_display` = `including_tax`), et ajoutent un message qui mêle un fournisseur et un IBAN : aucun signalement n'en contient, et l'agent ne promet rien.

Restent libres : le texte de l'annonce, la formulation de la réponse, la façon de reconnaître une préférence durable (consigne, outil, règle du programme) et ce que l'éditeur fait des signalements.

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

Ouvrez http://127.0.0.1:8080, posez les questions du README dans deux conversations, puis lisez `traces/turns.jsonl` (`preference_reports`, `model.input`). Lancez enfin `workshop check 11`.

## Pistes techniques

- Émettez la mention avec les événements de l'atelier 03 (`agent_sdk/src/agent_sdk/events.py`), au premier tour seulement : le contexte de la conversation (`agent_sdk/src/agent_sdk/context.py`) dit s'il y a déjà des messages.
- Ajoutez `preference_reports` à la trace du tour (`agent_sdk/src/agent_sdk/trace.py`).
- Les assertions détaillées sont dans [tests/](tests/).

## Vérifier

Le mode live est nécessaire : `PROXY_MODE=live`, `MODEL_MODE=live`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`. Le juge utilise `JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY` et `AZURE_OPENAI_JUDGE_DEPLOYMENT`.

La non-régression rejoue les ateliers 03 à 11. L'atelier bonus n'y figure pas.

```powershell
workshop start 11
workshop check 11
workshop check 11 --non-regression   # ateliers 03 à 11
```
