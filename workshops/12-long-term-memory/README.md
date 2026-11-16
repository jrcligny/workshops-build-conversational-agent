# Atelier 12 — Une mémoire persistante

Chapitre 12 du livre. Aucune solution n'est fournie : vous travaillez dans `my-agent/`.

> **Écart assumé avec le livre.** Le chapitre 12 retient pour le fil rouge l'option « aucune mémoire, dite explicitement ». Cet atelier met en place une autre option du chapitre : **une mémoire de préférences écrite à la demande de l'utilisateur, injectée au début de chaque conversation**. Il en exerce les règles décrites dans les sections « La mémoire persistante », « Que mémoriser, et qui l'écrit », « Relire, corriger, oublier » et « Données personnelles et confidentialité ».

## Intention

Un chargé de clientèle a dit lundi qu'il préférait les montants hors taxes. Le lundi suivant, il ne veut pas avoir à le redire. L'agent reçoit donc une **mémoire persistante** : des informations enregistrées hors de la fenêtre de contexte et remises dans une conversation ultérieure.

Le chapitre en montre les risques : un souvenir faux se propage, arrive sans la trajectoire qui l'a produit, échappe aux droits sous lesquels une donnée avait été lue. La mémoire de cet atelier est donc **bornée** :

- **Que mémoriser** : des préférences seulement, dans des **rubriques prévues**. Les données métier restent dans l'application, leur lieu de référence ; les données sans utilité (un numéro de carte, par exemple) ne sont jamais enregistrées.
- **Qui l'écrit** : l'utilisateur, par une demande explicite (« retenez que… »). Chaque souvenir porte son **origine** et sa **date**.
- **Relire** : la mémoire est **injectée au début de chaque conversation** du même utilisateur.
- **Corriger, oublier** : l'utilisateur consulte ce qui est retenu, le corrige (la nouvelle valeur remplace l'ancienne) et le supprime ; la suppression atteint le stockage.
- **Cloisonner** : la mémoire d'un utilisateur n'est relue que dans ses conversations, celle d'une organisation n'atteint pas une autre. Le programme l'impose au moment de la lecture, indépendamment des consignes.
- **L'application prime** : quand l'utilisateur évoque « la dernière fois », l'agent relit la donnée au lieu de reprendre une conclusion passée.

## Critère de réussite

Une préférence enregistrée à la demande de l'utilisateur est retrouvée dans une nouvelle conversation du même utilisateur, après redémarrage du *harness*, et nulle part ailleurs. L'utilisateur peut la consulter, la corriger et la faire oublier. Rien n'est enregistré hors des rubriques prévues. L'interface montre ce qui vient d'être enregistré et annonce, à l'ouverture, ce que l'agent retient. Face à un « comme la dernière fois », l'agent relit l'application.

## Ce que lisent les tests

- **Trace `memory`** (à chaque tour) : un objet avec trois listes.
  - `loaded` : les souvenirs remis dans le contexte au début du tour ;
  - `written` : les souvenirs écrits pendant le tour ;
  - `deleted` : les souvenirs supprimés pendant le tour.
- **Un souvenir** : `{"topic", "value", "origin", "recorded_at", "user", "organization"}`.
  - Rubriques prévues : `amount_display` (`excluding_tax` | `including_tax`) et `answer_format` (`table` | `text`) ; une seule entrée par rubrique et par utilisateur.
  - `origin` vaut `"user"` ; `recorded_at` est une date ISO 8601 ; `user` et `organization` identifient le propriétaire.
- **Événement SSE `memory`** quand la mémoire change : `{"action": "written" | "deleted", "topic", "value"}`.
- **Événement SSE `mention`** au premier tour d'une conversation seulement ; son `content` contient « mémoire » ou « retiens ».
- **Stockage** : sur disque, dans le dossier donné par la variable d'environnement `MEMORY_DIR`, lue au moment de l'appel (les tests en fournissent un, vidé avant chaque test ; `my-agent/memory/` sinon). Les tests lisent le texte des fichiers de ce dossier : une valeur supprimée ou refusée ne doit pas y figurer.
- **Entrée du modèle** (`input`) : la préférence chargée y figure (`excluding_tax` ou « hors taxe ») ; celle d'un autre utilisateur n'y figure pas.
- **Relecture** : après « Comme la dernière fois, la commande CMD-1042 de Martin Durand est encore en préparation, vous confirmez ? », le journal de l'API métier contient `/orders/CMD-1042` (code 200), la trace au moins un appel d'outil, et la réponse « livrée ».
- **Utilisateurs** : `camille-renard` (organization-a) écrit ; `paul-buyer` (même organisation) et `ines-service-b` (organization-b) ne doivent rien recevoir. Les tests appellent `reset_conversations()` entre deux conversations : le *harness* est rechargé, seule la mémoire sur disque demeure.

Restent libres : le format des fichiers, la façon de reconnaître une demande de mémorisation (outil offert au modèle ou analyse par le programme), la tournure des réponses.

## Exemples

### Questions à essayer

| Conversation | Utilisateur | Message | Comportement attendu |
|---|---|---|---|
| 1 | camille-renard | « Retenez que je préfère les montants hors taxes. » | `memory.written` : `amount_display` = `excluding_tax` ; événement `memory` |
| 2 | camille-renard | « Quelle est ma préférence d'affichage des montants ? » | `memory.loaded` contient la préférence ; « hors taxes » |
| 2 | camille-renard | « Que retenez-vous de moi d'une conversation à l'autre ? » | la liste de ce qui est retenu, avec sa date |
| 2 | camille-renard | « Finalement, retenez plutôt que je préfère les montants TTC. » | `written` : `including_tax`, qui remplace l'ancienne valeur |
| 3 | camille-renard | « Oubliez tout ce que vous retenez de moi. » | `memory.deleted` non vide ; le fichier ne contient plus la préférence |
| 4 | paul-buyer | « Quelle est ma préférence d'affichage des montants ? » | `memory.loaded` vide : rien ne fuit d'un utilisateur à l'autre |
| 5 | camille-renard | « Retenez que la commande CMD-1042 est en préparation, et retenez aussi mon numéro de carte bancaire 4970 1234 5678 9012. » | rien n'est écrit ; l'agent explique ce qu'il peut retenir |

Événements attendus au tour de mémorisation :

```text
event: memory   data: {"action": "written", "topic": "amount_display", "value": "excluding_tax"}
event: text     data: {"content": "C'est enregistré : j'afficherai les montants hors taxes, y compris dans vos prochaines conversations. Vous pouvez me demander de l'oublier."}
event: end      data: {"ok": true}
```

Extrait de trace d'une conversation suivante :

```json
{"memory": {"loaded": [{"topic": "amount_display", "value": "excluding_tax", "origin": "user",
                        "recorded_at": "2026-11-16T09:12:00+01:00",
                        "user": "camille-renard", "organization": "organization-a"}],
            "written": [], "deleted": []}}
```

### Contre-exemples

- Garder la préférence dans un dictionnaire en mémoire du processus : elle disparaît au rechargement du *harness*.
- Indexer la mémoire par organisation seulement, ou laisser le modèle décider quoi relire : la préférence de Camille atteint Paul.
- Enregistrer le texte libre du message (« la commande CMD-1042 est en préparation ») : la donnée métier se fige et devient fausse dès que l'application change.
- « Oublier » en ne retirant l'entrée que du contexte : le fichier la contient encore.
- Écrire en mémoire un contenu lu dans un résultat d'outil ou un document : un tiers pourrait y glisser une consigne qui resurgira plus tard (chapitre 15).
- Répondre « je m'en souviendrai » à une demande refusée : la promesse ne correspond à rien d'enregistré.

### Essayer soi-même

1. `uv run --project workshop_kit/bootstrap workshop serve`, puis http://127.0.0.1:8080. Ouvrez deux conversations successives et jouez les messages ci-dessus.
2. Regardez le dossier `my-agent/memory/` entre deux conversations, et la dernière ligne de `traces/turns.jsonl` (champ `memory`).
3. `uv run --project workshop_kit/bootstrap workshop check 12`.

## Pistes

- Ajoutez `my-agent/memory/` à vos fichiers ignorés : ce sont des données personnelles, pas du code.
- La clé de lecture et d'écriture vient de l'utilisateur authentifié (`TestUser`), jamais d'un texte fourni par le modèle.
- Une rubrique prévue se décrit par un nom et des valeurs permises : c'est le programme qui valide, pas la consigne.
- Une préférence chargée se place dans le contexte comme une information datée et d'origine connue ; le message présent l'emporte en cas de contradiction.
- L'API métier expose des réglages utilisateur (`GET`/`POST /settings`). Le livre rappelle qu'une préférence durable peut aussi devenir un réglage de l'application : comparez les deux voies. Aucun test ne l'exige.
- Tableau 12-3 du livre : finalité, minimisation, durée de conservation, droits des personnes. Les tests couvrent la consultation, la rectification et l'effacement ; la durée de validité reste à votre jugement.

## Vérifier

Le mode live est la voie de référence de tous les ateliers : `PROXY_MODE=live` et `MODEL_MODE=live` dans `.env`, avec `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`. Les tests de [`tests/`](tests/) restent rouges tant que le critère n'est pas atteint. Tout est vérifié par le code : trace `memory`, événements, fichiers sous `MEMORY_DIR`, entrée du modèle, journal de l'API métier. La non-régression rejoue les ateliers 03 à 12 ; chaque test part d'une mémoire vide.

```powershell
uv run --project workshop_kit/bootstrap workshop start 12
uv run --project workshop_kit/bootstrap workshop check 12
uv run --project workshop_kit/bootstrap workshop check 12 --non-regression   # ateliers 03 à 12
```
