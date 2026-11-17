# Atelier 10 — Contrat vérifié par les tests

Ce document détaille ce que vérifient les tests de l'atelier ; l'objectif de l'atelier est présenté dans [README.md](README.md).

## Conversations écrites, un seul tour joué

Les tests ne jouent pas les tours anciens : ils **chargent une conversation déjà écrite** (`tests/cases.yaml`, `scenario.conversation`) dans le contexte de votre agent, avec `POST /conversations/{id}/history`, puis jouent en direct le seul tour vérifié. Cette conversation contient de vrais échanges métier : messages de l'utilisateur, appels d'outils avec leurs arguments et leurs résultats, réponses de l'agent. Les noms d'outils y sont neutres (`search_customers`, `list_orders`, `get_order`) : votre agent rejoue ces messages tels quels, même si ces outils ne sont pas ceux qu'il propose, et n'appelle que ses propres outils.

Les faits clés (la cliente choisie entre deux homonymes, sa commande, son statut, son montant) ne figurent **que** dans des résultats d'outils et des réponses de l'agent, jamais dans un message de l'utilisateur conservé tel quel.

Une conversation chargée arrive **sans état** (`ctx.state` est vide) : votre agent reconstruit sa mémoire de travail à partir des messages du contexte, avant de compacter.

## Réglages lus à l'exécution

- `COMPACTION_MESSAGE_THRESHOLD` (`settings.compaction_message_threshold`, 8 par défaut) : nombre de **tours** stockés dans le contexte au début du tour à partir duquel le tour compacte. Un tour = un message de l'utilisateur, les appels d'outils et leurs résultats, la réponse.
- `COMPACTION_KEEP_TURNS` (`settings.compaction_keep_turns`, 2 par défaut) : nombre de derniers tours gardés tels quels.
- Les tests changent ces valeurs (public : 8 et 2 ; privé : d'autres valeurs). Lisez-les à chaque tour, sans les recopier dans une constante.

## Ce que lisent les tests

### Sous le seuil

Avec `threshold - 1` tours chargés, le tour ne compacte pas : la trace n'a pas de clé `compaction`, et `input.history` rejoue **tout** le contexte tel quel, dans l'ordre (messages de l'utilisateur, messages `assistant` avec leurs `tool_calls`, messages `tool` avec leurs résultats, réponses).

### Le tour qui compacte

Avec `threshold` tours chargés, le tour compacte, en deux étapes, et la trace contient un objet `compaction` :

| Champ | Contenu exigé |
| --- | --- |
| `threshold` | le seuil réglé |
| `kept_turns` | `COMPACTION_KEEP_TURNS` |
| `cleared_tool_results` | étape a : une entrée `{tool_call_id, name, turn}` par résultat d'outil ancien remplacé par un marqueur ; **tous** les résultats de la conversation chargée y figurent |
| `summarized_turns` | étape b : `threshold - kept_turns`, les tours remplacés par le résumé |
| `system_prompt` | le prompt de compaction envoyé : `my-agent/compaction_prompt.md` sans ses commentaires HTML, différent du prompt système de l'agent |
| `previous_summary` | le résumé précédent (vide à la première compaction) |
| `summary` | le résumé mis à jour, sous cinq rubriques fixes |
| `model_call` | l'appel au modèle dédié au résumé (`Tracer.compaction_call`) |

`Tracer.compaction(...)` et `Tracer.compaction_call(...)` de `agent_sdk` écrivent cet objet et renvoient l'événement d'interface.

- **Étape a, effacement des résultats d'outils.** Dans `input.history`, les tours gardés conservent leurs appels d'outils (même `id`) et un message `tool` pour chacun, mais son contenu est un marqueur non vide, jamais le résultat d'origine. Aucun résultat d'outil de la conversation chargée n'est rejoué tel quel.
- **Étape b, résumé glissant.** Seuls les messages de l'utilisateur des `kept_turns` derniers tours sont rejoués tels quels ; `input.message` est le message courant ; le résumé envoyé au modèle (par exemple dans un message système après le prompt de l'agent, comme le fait `Context.for_model`) se retrouve tel quel dans `input` : tracez-le, par exemple avec `tracer.input(..., summary=ctx.summary)`.
- **Appel séparé.** Le journal du proxy enregistre l'empreinte (`system_sha256`) du message système de chaque appel : l'un des appels du tour a pour message système le prompt de compaction, un autre celui de l'agent.
- **Le résumé glisse.** Après la compaction, les tests ajoutent `threshold - kept_turns - 1` tours écrits (`continuation`, mode `append`) ; le tour suivant compacte à nouveau, et son `previous_summary` est exactement le résumé précédent.
- **Interface.** Le tour qui compacte émet un événement `compaction` ou `mention` dans le flux SSE.

### Le résumé, jugé

Le résumé (`compaction.summary`) est soumis au juge sémantique avec, comme trace, les résultats d'outils de la conversation chargée. La rubrique `10-summary-keeps-tool-facts` exige :

- les cinq rubriques, dans ces termes : `Objectif de l'utilisateur`, `Entités en cours`, `Faits établis`, `Décisions et choix confirmés`, `Questions en suspens` ;
- les faits lus par les outils : la cliente Léa Martin de Lille, choisie entre deux homonymes ; CMD-2010, expédiée, 450 ; la réclamation sur le prix ; le rappel souhaité en fin de semaine, encore en suspens.

Un résumé vide, générique, tronqué ou en prose sans rubriques échoue.

### Répondre depuis le résumé

Au tour qui compacte, la question « Sans relire la commande, rappelez-moi son montant. » obtient une réponse qui donne 450, alors que ce montant n'existe plus que dans le résumé : aucune lecture de commande n'apparaît dans le journal de l'API métier pendant ce tour.

### Mémoire de travail

- `state` : l'état de conversation **après** le tour, objet non vide, lu à chaque tour vérifié.
- `input.state` : l'état remis au modèle **au début** du tour.
- Champs imposés : `current_customer` (`id`, `name`, `city`), `current_order` (`reference`), `candidates` (exactement 2 tant que le choix entre homonymes est en attente).
- Au tour qui compacte, `input.state` contient la cliente et la commande en cours, reconstruites depuis la conversation chargée ; « Et celle-là, où en est-elle ? » porte sur CMD-2010 (référence dans les arguments d'un outil, ou statut dans la réponse).
- Le choix entre homonymes, fait sur deux tours joués, survit à une compaction : après le remplissage écrit (`filler`), le tour compacte, `state.current_customer.city` est toujours Lille, et la réponse parle de Lille, jamais de Lyon.
- Au changement de client, `current_customer` est remplacé et l'ancienne commande disparaît de `current_order`.
- Libre : les autres champs de l'état, sa forme dans le message envoyé au modèle, le texte du marqueur, la façon de rédiger le résumé à l'intérieur des rubriques.

Utilisateur : camille-renard (`customer_service`, `organization-a`), jeu de données `standard`.

## Exemple de trace du tour qui compacte

```json
{
  "compaction": {
    "threshold": 8,
    "kept_turns": 2,
    "cleared_tool_results": [{"tool_call_id": "call_1_0", "name": "search_customers", "turn": 1}],
    "summarized_turns": 6,
    "system_prompt": "Tu résumes une conversation de service client…",
    "previous_summary": "",
    "summary": "## Objectif de l'utilisateur\n…\n## Faits établis\n- CMD-2010 : expédiée, 450 € (get_order)\n…",
    "model_call": {"model": "default", "usage": {"input_tokens": 1200, "output_tokens": 180}}
  },
  "input": {
    "state": {"current_customer": {"id": "C-MARTIN-LILLE", "name": "Léa Martin", "city": "Lille"}, "current_order": {"reference": "CMD-2010"}}
  }
}
```

### Contre-exemples

- Garder le premier message de l'utilisateur mot pour mot et compter sur lui : les faits n'y sont pas, le juge échoue.
- Rédiger le résumé avec le prompt de l'agent, ou dans le même appel que la réponse : l'empreinte du prompt de compaction est absente du journal.
- Effacer les résultats d'outils en supprimant aussi les appels : le modèle reçoit des réponses sans leurs appels, le test d'effacement échoue.
- Repartir de zéro à chaque compaction : `previous_summary` est vide à la deuxième.
- Un état écrit dans la trace sans être remis au modèle : `input.state` est absent.

## Ce qui demande le mode live

Le simulateur du proxy ne rédige pas de vrai résumé : le jugement du résumé, la réponse depuis le résumé, la mémoire de travail et les homonymes ne se vérifient qu'en mode live (voir [Vérifier](#vérifier)). L'effacement, le prompt dédié, le seuil et l'interface se vérifient aussi en mode simulé.

## Essayer soi-même

1. Lancez `uv run --project tooling/cli workshop serve`, puis ouvrez http://127.0.0.1:8080.
2. Pour charger une conversation écrite, envoyez-la à `POST http://127.0.0.1:8000/conversations/{id}/history` (corps `{"messages": [...], "append": false}`, des messages de chat complets ; `ChatClient.load` les produit depuis le format de `scenario.conversation`), puis jouez un tour.
3. Ouvrez `traces/turns.jsonl` : sur la dernière ligne, lisez `compaction`, puis `input.history` et `input.state`.
4. Lancez `workshop check 10`.

## Pistes techniques

- Les réglages sont dans `shared/workshop_config/src/workshop_config/__init__.py` (`compaction_message_threshold`, `compaction_keep_turns`).
- Le contexte de la conversation est `agent_sdk.context` : `ctx.messages` (messages complets), `ctx.summary` (le résumé courant, placé par `for_model` après le prompt système), `ctx.state` (la mémoire de travail, hors des messages) et `replace(...)`.
- `Tracer.compaction_call(client, messages)` fait l'appel au modèle du résumé sans outils ; `Tracer.compaction(...)` écrit la trace et renvoie l'événement à émettre. `mention(...)` de `agent_sdk.events` construit un message d'information.
- Le contrat de la trace est décrit dans `docs/interface-contract.md` et `agent_sdk/src/agent_sdk/contract.py`.
- Les données sont dans `business/business_api/src/business_api/seed_data.py`.

## Vérifier

Le mode live est la voie de référence de tous les ateliers (indispensable depuis l'atelier 04). Dans `.env`, mettez `PROXY_MODE=live` et `MODEL_MODE=live`, et renseignez `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Les tests restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par le code (trace, journal, événements) est vérifié d'abord. La rubrique du résumé est jugée par le juge sémantique s'il est configuré (`JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY`), et répétée selon la règle k sur n (`JUDGE_K` réussites sur `JUDGE_N` essais, 3 sur 5 par défaut).

La non-régression rejoue les ateliers 03 à 10. Seuls les tests de l'atelier 03 sont marqués `superseded_by("04")`. Aucun test de cet atelier n'est marqué.

```powershell
uv run --project tooling/cli workshop start 08
uv run --project tooling/cli workshop check 10
uv run --project tooling/cli workshop check 10 --non-regression   # ateliers 03 à 10
```
