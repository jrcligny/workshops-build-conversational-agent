# Atelier 16 — De la consigne au contrôle

Chapitre 16 du livre. Aucune solution n'est fournie : vous travaillez dans `my-agent/`.

## Intention

Une consigne influence le modèle ; un invariant, une validation ou un contrôle s'applique quelle que soit sa sortie. Pour chaque règle du fil rouge, le chapitre pose la question : que se passe-t-il si le modèle ne la suit pas ? L'équipe retient le **doublement selon la conséquence** : une règle dont la violation touche l'utilisateur ou les données reçoit un contrôle du *harness*, qui garde sa consigne, et qui rend l'écart visible lorsqu'il ne peut pas l'empêcher. Trois règles sont doublées (résultats partiels, ambiguïtés, sources), et les conversations simultanées sont isolées : la description de l'agent est partagée, mais mémoire de travail, *skills* chargés, marquage et identité appartiennent à chaque conversation.

## Critère de réussite

Une réponse fondée sur un résultat borné porte, sous la réponse, une mention construite par le *harness* à partir des indications de l'outil (liste partielle, total). Quand la résolution d'un nom renvoie plusieurs candidats, le client en cours n'est enregistré qu'après le choix de l'utilisateur. Une commande ou une facture citée sans figurer parmi les enregistrements consultés est signalée comme non vérifiée. Deux conversations simultanées ne partagent ni état ni identité.

## Ce que lisent les tests

- **Événement SSE `mention`**, champ `data.content`. Les tests concatènent le `content` de toutes les mentions du tour.
- **Résultat borné** (jeu `volume`, client « Transports Morel ») : au moins un appel avec `tools[].result.truncated` vrai (atelier 07). La mention contient `partiel` et le total renvoyé par l'application pour `filter="late"` (60 commandes en retard dans `volume`).
- **Homonymes** (« Léa Martin », Lille et Lyon) : après la question, `state.candidates` contient exactement 2 éléments et `state.current_customer` est vide. Après « Celle de Lille. », `state.current_customer.city` vaut `"Lille"`.
- **Références inexistantes** `FAC-9999` et `CMD-0000` : chacune est cherchée dans l'application (un appel dont les `arguments` la contiennent) ; tous ces appels ont `tools[].result.status` = `not_found` ; une mention cite les deux références.
- **Isolement** : conversation A (`camille-renard`, `customer_service`) → `state.current_order.reference` = `"CMD-1042"`. Conversation B (`paul-buyer`, `buyer`), ouverte en parallèle → `state.current_order` et `state.current_customer` vides, et ni « Durand » ni `CMD-1042` dans la réponse. De retour dans A, « Et son client ? » → la réponse cite Durand.
- Champs de trace hérités : `state` (atelier 08 : `current_customer`, `candidates`, `current_order`), `tools[].result.status`, `total` et `truncated` (atelier 07).

Restent libres : la formulation des mentions (tant qu'elles contiennent les éléments ci-dessus), la forme des candidats dans `state.candidates`. Aucune rubrique de juge dans cet atelier : tout est vérifié par le code.

## Exemples

### Questions à essayer

| Message | Comportement attendu |
|---|---|
| « Listez toutes les commandes en retard de Transports Morel. » (jeu `volume`) | Liste bornée, puis mention « Liste partielle : 60 commandes en retard au total » |
| « Quelles sont les commandes de Léa Martin ? » | Deux candidates, question sur la ville, aucun client en cours |
| « Celle de Lille. » | Client en cours : Léa Martin, Lille (CMD-2010) |
| « La facture FAC-9999 et la commande CMD-0000 sont-elles réglées ? » | Deux recherches `not_found`, mention « Références non vérifiées : FAC-9999, CMD-0000 » |
| A : « Quel est le statut de la commande CMD-1042 de Martin Durand ? » puis B : « Qui est le client en cours, et quelle commande est-ce que je suis ? » | B n'a ni client ni commande en cours |

Séquence SSE attendue pour la liste bornée :

```text
event: text      data: {"content": "Voici les premières commandes en retard ..."}
event: mention   data: {"content": "Liste partielle : 60 commandes en retard au total, seules les premières sont affichées."}
event: end       data: {"ok": true}
```

Extrait de trace après la question sur Léa Martin :

```json
{"state": {"current_customer": null,
           "candidates": [{"id": "C-MARTIN-LILLE", "city": "Lille"}, {"id": "C-MARTIN-LYON", "city": "Lyon"}]}}
```

### Contre-exemples

- Demander au modèle d'écrire « liste partielle » dans sa réponse : le test lit l'événement `mention`, pas le texte.
- Une mention « vérifiez vos références » sans citer `FAC-9999` et `CMD-0000` : le test exige les deux références.
- Répondre « ces références n'existent pas » sans les chercher : chaque référence doit apparaître dans les arguments d'un appel d'outil.
- Enregistrer la première Léa Martin trouvée comme client en cours : `state.current_customer` doit rester vide avant le choix.
- Ranger l'état de travail dans un attribut du *harness* partagé entre conversations : la conversation B verrait CMD-1042.

### Essayer soi-même

Lancez `uv run --project workshop_kit/bootstrap workshop serve` (ajoutez `--reset-data` pour repartir des données), puis ouvrez http://127.0.0.1:8080. Posez les questions ci-dessus. L'interface de chat n'affiche pas encore l'événement `mention` : lisez la dernière ligne de `traces/turns.jsonl` (`state`, `tools`) ou lisez le flux SSE de `POST http://127.0.0.1:8000/conversations/{id}/messages`. Pour l'isolement, ouvrez deux onglets. Puis lancez `workshop check 16`.

## Pistes

- Relisez le tableau 16-3 du chapitre : il recense les règles et leur lieu. Ne doublez que celles dont la violation touche l'utilisateur.
- La mention des résultats partiels se construit à partir de `truncated` et `total` du résultat d'outil (atelier 07), pas à partir du texte du modèle.
- Les « enregistrements consultés » sont les références présentes dans les résultats `ok` du tour ; une référence citée ou cherchée sans résultat `ok` est non vérifiée.
- La mémoire de travail de l'atelier 08 doit être indexée par conversation ; vérifiez qu'aucune donnée d'une conversation ne vit dans un attribut partagé du *harness*.
- Un contrôle du *harness* s'applique quel que soit le texte produit par le modèle : ne comptez pas sur une instruction du *prompt système* pour le remplacer.
- Le jeu `volume` est chargé par le test (`observation.reset("volume")`) ; les autres tests utilisent `standard`.

## Vérifier

Prérequis : le mode live est la voie de référence de tous les ateliers (`PROXY_MODE=live` et `MODEL_MODE=live` dans `.env`, avec `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT`). Les tests de [`tests/`](tests/) restent rouges tant que le critère n'est pas atteint. Tout est vérifié par le code : événements `mention`, champs `state` et `tools` de la trace, données de l'application. Lancez la non-régression : les contrôles ajoutés ne doivent pas casser la compaction (07), la mémoire de travail (08) ni les *skills* (14).

```powershell
uv run --project workshop_kit/bootstrap workshop start 16
uv run --project workshop_kit/bootstrap workshop check 16
uv run --project workshop_kit/bootstrap workshop check 16 --non-regression   # ateliers 03 à 16
```
