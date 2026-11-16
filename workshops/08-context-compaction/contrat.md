# Atelier 08 — Contrat vérifié par les tests

Ce document détaille ce que vérifient les tests de l'atelier ; l'objectif de l'atelier est présenté dans [README.md](README.md).

## Ce que lisent les tests

### Compaction

- `compaction` : un objet présent seulement sur le tour qui compacte, avec `summarized_answers` (au moins 1), `kept_user_messages` (au moins 1 : les messages utilisateur anciens gardés mot pour mot), `threshold` (le seuil réglé, `COMPACTION_MESSAGE_THRESHOLD`, 8 par défaut) et `summary` (le texte du résumé, non vide, qui doit se retrouver tel quel dans `input` : historique, prompt système ou autre champ) ; la clé est absente sous le seuil.
- Dans le flux SSE, le tour qui compacte émet un événement `compaction` ou `mention`.
- Sous le seuil : la demande initiale est rejouée telle quelle dans `input.history`, et la trace ne contient pas de clé `compaction`.
- Au-delà du seuil : chaque message précédent de l'utilisateur figure mot pour mot dans `input.history` (rôle `user`), `input.message` est le message courant, et l'historique contient moins de réponses `assistant` que de tours précédents.
- Restent libres : le contenu et la place du résumé dans l'entrée, le moment exact de la compaction.

Exemple : « Je traite le dossier de Martin Durand, commande CMD-1042, commandes livrées uniquement. » suivi de dix messages « Détail numéro 1 : je veux seulement les commandes livrées de CMD-1042. »… → sur le tour qui compacte, la trace contient `{"compaction": {"summarized_answers": 4, "kept_user_messages": 10, "threshold": 8, "summary": "Le conseiller suit CMD-1042…"}}` et le flux émet `{"type": "compaction", ...}`. L'interface Chainlit n'affiche ni `compaction` ni `mention` : suivez le flux avec `curl.exe -N` sur `http://127.0.0.1:8000/conversations/{id}/messages` (corps `{"text": "..."}`).

La compaction porte sur ce que vous envoyez au modèle ; le *harness* reçoit l'historique complet de l'interface à chaque tour.

### Mémoire de travail

Les tests sont dans [tests/](tests/). Ils lisent la trace du tour (`traces/turns.jsonl`, dernière ligne).

- `state` : l'état de conversation **après** le tour. C'est un objet non vide, imposé à chaque tour où le test le lit.
- `input.state` : l'état remis au modèle **au début** du tour (lu au dernier tour du premier test).
- Champs imposés dans l'état :
  - `current_customer` : objet avec `id`, `name`, `city` (les tests lisent `name` et `city`) ;
  - `current_order` : objet avec `reference` ;
  - `candidates` : liste des homonymes tant que le choix est en attente (exactement 2 pour Léa Martin).
- `tools[].arguments` : le test 1 y cherche `CMD-1042`, ou à défaut le mot « livrée » dans la réponse.
- Le seuil de compaction est `COMPACTION_MESSAGE_THRESHOLD` (8 par défaut). Les tests jouent seuil + 2 tours (10 tours) de remplissage pour le dépasser.
- Utilisateur : camille-renard (`customer_service`, `organization-a`), jeu de données `standard`.
- Libre : les autres champs de l'état, sa forme dans le message envoyé au modèle, la manière de le mettre à jour.
- Aucune rubrique jugée dans cet atelier : tout se vérifie par la trace.

## Exemples de traces

Données : CMD-1042 appartient à Martin Durand (Nantes) et elle est livrée. Il y a deux clientes Léa Martin, l'une à Lille (C-MARTIN-LILLE), l'autre à Lyon (C-MARTIN-LYON). Transports Morel (C-VOLUMEX) est un client de Rennes.

1. « Quel est le statut de la commande CMD-1042 de Martin Durand ? », puis dix tours « D'accord, continuez à suivre ce dossier (0). » à « (9). », puis « Et celle-là, où en est-elle ? ». Au dernier tour, la trace contient au moins :

```json
{
  "input": {
    "state": {
      "current_customer": {"id": "C-DURAND-1", "name": "Martin Durand", "city": "Nantes"},
      "current_order": {"reference": "CMD-1042"}
    }
  },
  "tools": [{"name": "…", "arguments": {"reference": "CMD-1042"}}]
}
```

   Le nom de l'outil et de ses arguments est libre ; le test cherche seulement `CMD-1042` dans les arguments. La réponse dit que la commande est livrée.

2. « Quelles sont les commandes de Léa Martin ? » : l'agent demande laquelle, et l'état garde les deux candidates.

```json
{"state": {"candidates": [{"id": "C-MARTIN-LILLE", "city": "Lille"}, {"id": "C-MARTIN-LYON", "city": "Lyon"}]}}
```

   Puis « Celle de Lille, s'il vous plaît. » donne `state.current_customer.city` = `"Lille"`. Le contenu de chaque candidat est libre : le test compte seulement deux éléments. Après dix tours « Merci, restons sur ce dossier (i). », la question « Rappelez-moi le client en cours. » obtient une réponse qui parle de Lille et jamais de Lyon.

3. « Quel est le statut de la commande CMD-1042 de Martin Durand ? », puis « Passons maintenant à Transports Morel : combien a-t-il de commandes ? ».

```json
{"state": {"current_customer": {"id": "C-VOLUMEX", "name": "Transports Morel", "city": "Rennes"}, "current_order": null}}
```

   L'ancienne commande n'est plus dans `current_order`.

### Contre-exemples techniques

- L'état n'est écrit que dans la trace, sans être remis au modèle : `input.state` est absent et le test 1 échoue.
- Au changement de client, seul `current_customer` est remplacé : `current_order` contient encore CMD-1042, c'est une mémoire périmée, et le test 3 échoue.
- Une réponse qui cite Lille et Lyon « pour être sûr » échoue : le test exige Lille et interdit Lyon.

## Essayer soi-même

1. Lancez `uv run --project workshop_kit/bootstrap workshop serve`, puis ouvrez http://127.0.0.1:8080.
2. Jouez la séquence 1 ci-dessus.
3. Après chaque tour, ouvrez `traces/turns.jsonl`. Sur la dernière ligne, comparez `state` et `input.state` : le second est l'état reçu au début du tour, le premier l'état après le tour.
4. Lancez `workshop check 08`.

## Pistes techniques

- Le seuil vient de `workshop_kit/shell/config.py` (`compaction_message_threshold`) ; il se règle avec `COMPACTION_MESSAGE_THRESHOLD` dans `.env`. Lisez `settings.compaction_message_threshold` à chaque tour, sans le recopier dans une constante ni écrire 8 en dur : la valeur réglée peut changer.
- Le contrat de la trace (`state`, `input`) est décrit dans `docs/interface-contract.md` et dans `agent_sdk/src/agent_sdk/contract.py`. `compaction(...)` et `mention(...)` de `agent_sdk/src/agent_sdk/events.py` construisent l'événement ; le seuil, le résumé et ce qui est conservé restent à vous.
- Les homonymes viennent de la résolution de noms des ateliers 05 et 06 ; les données sont dans `workshop_kit/apps/business_api/seed_data.py`.

## Vérifier

Le mode live est la voie de référence de tous les ateliers (indispensable depuis l'atelier 04). Dans `.env`, mettez `PROXY_MODE=live` et `MODEL_MODE=live`, et renseignez `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`.

Les tests restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par le code (état de l'application, trace, journal, événements) est vérifié d'abord. Cet atelier n'a pas de rubrique de sens. Ailleurs, une rubrique est jugée par un juge sémantique s'il est configuré (`JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY`), et répétée selon la règle k sur n (`JUDGE_K` réussites sur `JUDGE_N` essais, 3 sur 5 par défaut).

La non-régression rejoue les ateliers 03 à 08. Seuls les tests de l'atelier 03 sont marqués `superseded_by("04")` : ils sont ignorés quand l'atelier visé est 04 ou plus. Aucun test de cet atelier n'est marqué.

```powershell
uv run --project workshop_kit/bootstrap workshop start 08
uv run --project workshop_kit/bootstrap workshop check 08
uv run --project workshop_kit/bootstrap workshop check 08 --non-regression   # ateliers 03 à 08
```
