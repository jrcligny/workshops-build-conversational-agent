# Atelier 04 — Premier outil

Chapitre 4 du livre. Vous travaillez dans `my-agent/` ; aucune solution n'est fournie.

## Ce que vous allez construire

L'agent reçoit son premier outil : lire une commande à partir de sa référence. Le partage
des rôles est net : le modèle demande, le programme exécute. Avant d'exécuter, le
programme vérifie les arguments ; après, il renvoie un résultat de forme stable : trouvé,
proche, introuvable ou erreur. Retrouver une référence mal saisie est le travail de
l'outil, pas du modèle. Et les commandes exclues (supprimées ou rejetées) le restent,
y compris dans les suggestions.

## C'est réussi quand…

- pour une référence connue, l'agent consulte l'outil puis donne le statut qu'il a lu ;
- pour une référence proche d'une commande existante, il nomme les deux références et
  propose la commande proche sans présenter son statut comme la réponse ;
- pour une commande exclue, il répond qu'elle est introuvable, sans révéler qu'elle a existé ;
- une référence mal formée est rejetée par l'outil avant toute consultation de
  l'application métier ;
- chaque question donne lieu à un seul appel d'outil (l'outil, lui, peut interroger
  plusieurs fois l'application métier).

## Exemples

| Question posée à l'agent | Ce que l'agent doit faire |
|---|---|
| « Quel est le statut de la commande CMD-1042 de Martin Durand ? » | Il lit la commande avec l'outil, puis répond qu'elle est livrée. |
| « Quel est le statut de la commande CMD-1402 ? » | Il ne trouve pas CMD-1402 et demande : « Pensiez-vous à CMD-1042 ? » |
| « Quel est le statut de la commande CMD-0881 ? » | Il répond qu'il ne trouve pas cette commande, sans autre détail. |
| « Quel est le statut de la commande 1042;DROP ? » | Il demande une référence au format CMD-NNNN ; l'application métier n'est pas interrogée. |

## À éviter

- Répondre « CMD-1402 est livrée » : cette commande n'existe pas.
- Dire que CMD-0881 a été supprimée : l'exclusion doit rester invisible.
- Appeler l'outil deux fois pour une seule question.
- Laisser le modèle deviner la référence proche : c'est le rôle de l'outil.

## Pistes

- Décidez ce que l'outil renvoie dans chaque cas (trouvé, proche, introuvable, erreur) :
  une forme stable aide le modèle à formuler la bonne réponse.
- L'application métier ne sait pas chercher « à peu près » : c'est à votre outil de
  calculer les références candidates et de ne garder que celles qui existent. Ici, une
  référence proche est la même référence avec deux chiffres voisins inversés (CMD-1402 →
  CMD-1042). Limitez le nombre de candidats : chaque vérification est une requête HTTP.
- « Un seul appel d'outil » se compte côté modèle : l'outil, lui, peut faire plusieurs
  requêtes à l'application métier (la référence demandée, puis ses candidates).
- Vérifiez le format de la référence avant tout appel : une entrée invalide ne doit jamais
  atteindre l'application. Décrivez l'outil pour que le modèle lui transmette la référence
  telle que l'utilisateur l'a écrite, sans la valider lui-même : c'est l'outil qui la
  rejette, avec un résultat `error`.
- Une commande exclue ne doit apparaître nulle part, même comme suggestion.

### Le tour avec outil, pas à pas

Le modèle n'exécute rien : il *demande* un appel, que votre programme (le *harness*) exécute.
Un tour avec outil compte donc au moins deux appels au modèle, au format *chat completions*
du proxy (`POST /v1/chat/completions`, via `model_client().generate(messages, tools)`) :

1. **Envoi des outils.** Le harness envoie les messages et la déclaration de l'outil
   (`tools`, construite par `declare(fonction)`).
2. **Réponse `tool_calls`.** Au lieu d'un texte, le modèle renvoie, dans
   `choices[0].message`, une liste `tool_calls` : chaque appel porte un `id`, le nom de
   l'outil et ses `arguments`, une **chaîne JSON** à décoder (`json.loads`).
3. **Exécution par le harness.** Le harness vérifie les arguments, exécute l'outil (ici
   `GET /orders/{reference}`) et enregistre l'appel dans la trace.
4. **Message `tool`.** Le harness ajoute aux messages le message assistant tel quel (avec ses
   `tool_calls`), puis un message `role: "tool"` par appel, dont `tool_call_id` reprend l'`id`
   de l'appel et dont `content` est le résultat en texte JSON.
5. **Second appel au modèle.** Le harness rappelle le modèle avec ces messages ; le modèle lit
   le résultat et répond par un texte sans `tool_calls`. Tant qu'il renvoie des `tool_calls`,
   on recommence à l'étape 3 (la boucle de l'atelier 05).

Aller-retour pour « Quel est le statut de la commande CMD-1042 ? ». Corps du premier appel
(étape 1) :

```json
{"model": "default", "stream": false,
 "messages": [{"role": "system", "content": "Vous êtes l'assistant du service client…"},
              {"role": "user", "content": "Quel est le statut de la commande CMD-1042 ?"}],
 "tools": [{"type": "function",
            "function": {"name": "get_order", "description": "Lit une commande par sa référence.",
                         "parameters": {"type": "object",
                                        "properties": {"reference": {"type": "string"}},
                                        "required": ["reference"]}}}]}
```

Réponse du modèle, `choices[0].message` (étape 2) :

```json
{"role": "assistant", "content": null,
 "tool_calls": [{"id": "call_1", "type": "function",
                 "function": {"name": "get_order", "arguments": "{\"reference\": \"CMD-1042\"}"}}]}
```

Messages ajoutés avant le second appel (étape 4) : ce message assistant, puis

```json
{"role": "tool", "tool_call_id": "call_1", "name": "get_order",
 "content": "{\"status\": \"ok\", \"order\": {\"reference\": \"CMD-1042\", \"status\": \"delivered\"}}"}
```

Réponse du second appel (étape 5) :
`{"role": "assistant", "content": "La commande CMD-1042 est livrée."}`. Enregistrez tous ces
messages dans le contexte de la conversation : au tour suivant, le modèle doit les revoir.

## Pour aller plus loin

Le détail de ce que vérifient les tests (noms attendus dans la trace, événements, rubriques)
est dans [contrat.md](contrat.md). Pour lancer l'atelier et ses tests, voir le
[guide de démarrage](../../GETTING_STARTED.md).
