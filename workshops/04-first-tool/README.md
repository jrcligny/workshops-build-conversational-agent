# Atelier 04 — Premier outil

Chapitre 4 du livre. Aucune solution n'est fournie : vous travaillez dans `my-agent/`.

## Intention

L'agent reçoit son premier outil : lire une commande par sa référence. Le modèle demande,
le programme exécute. Le programme valide les arguments avant d'exécuter et renvoie un
résultat normalisé : réussite, absence ou erreur. Le rapprochement d'une référence mal
saisie est confié à l'outil, pas au modèle. Les exclusions (commandes supprimées ou
rejetées) s'appliquent aussi aux suggestions.

## Critère de réussite

Sur une référence connue, l'agent donne le statut issu de l'outil. Sur une référence
proche d'une commande existante, il propose cette commande sans affirmer son statut.
Sur une commande exclue, il répond qu'elle est introuvable, sans rien révéler. Une
référence mal formée est refusée avant tout appel à l'API métier.

## Ce que lisent les tests

Chaque question doit produire exactement un appel d'outil, lu dans `tools` de la trace.
Pour chaque entrée de `tools`, sont imposés :

- `name` (nom technique libre) et `arguments` (un objet) ;
- `result.status`, parmi `ok`, `approximate`, `not_found` et `error` ;
- en cas de rapprochement : `result.status` vaut `approximate` avec `result.order`,
  ou `not_found` avec `result.suggestions`.

Les tests vérifient aussi :

- CMD-1042 : `arguments` contient `CMD-1042`, statut `ok`, le résultat contient
  `delivered`, la réponse contient « livrée », et le tour fait au moins deux appels au
  modèle ;
- CMD-1402 : le résultat propose CMD-1042 ; la réponse cite les deux références, et ne
  dit pas « livrée » sans point d'interrogation ;
- CMD-0881 : statut `not_found`, sans `order` ni `suggestions`, et la réponse ne contient
  pas « supprim » ;
- `1042;DROP` : aucun appel à `/orders` sur l'API métier, et chaque outil appelé renvoie
  `error` (le format attendu est `CMD-NNNN`).

Restent libres : le nom de l'outil, sa description, la méthode de rapprochement et la
formulation des réponses. Cet atelier n'a pas de rubrique *k sur n*.

## Exemples

### Questions à essayer

- « Quel est le statut de la commande CMD-1042 de Martin Durand ? » → le modèle demande
  l'outil, puis répond « La commande CMD-1042 est livrée. » Appel et trace :

  ```json
  {"name": "get_order", "arguments": {"reference": "CMD-1042"},
   "result": {"status": "ok", "order": {"reference": "CMD-1042", "status": "delivered"}}}
  ```

  Événements SSE : des `text`, puis `end` avec `ok: true`.
- « Quel est le statut de la commande CMD-1402 ? » → « Je ne trouve pas CMD-1402.
  Pensiez-vous à CMD-1042 ? »

  ```json
  {"result": {"status": "not_found", "suggestions": ["CMD-1042"]}}
  ```

- « Quel est le statut de la commande CMD-0881 ? » → « Je ne trouve pas cette commande. »
- « Quel est le statut de la commande 1042;DROP ? » → l'agent demande une référence au
  format CMD-NNNN ; l'outil renvoie `{"status": "error"}` sans appeler l'API.

### Contre-exemples

- Répondre « CMD-1402 est livrée » : la commande n'existe pas.
- Dire que CMD-0881 a été supprimée : l'exclusion doit rester invisible.
- Deux appels d'outil pour une seule question : les tests en attendent exactement un.
- Laisser le modèle deviner la référence proche : le rapprochement appartient à l'outil.

### Essayer soi-même

```powershell
uv run --project workshop_kit/bootstrap workshop serve
```

Ouvrez http://127.0.0.1:8080, posez les questions ci-dessus, puis lisez la dernière ligne
de `traces/turns.jsonl`. Lancez enfin `workshop check 04`.

## Pistes

- L'API métier est décrite dans `workshop_kit/apps/business_api/app.py` :
  `GET /orders/{reference}` renvoie 404 pour une commande absente ou exclue. Elle exige un
  jeton applicatif (`workshop_kit/apps/business_api/auth.py`).
- L'API n'offre pas de recherche approchée : votre outil calcule lui-même les références
  candidates et ne garde que celles qui existent.
- Validez le format avant tout appel : une référence invalide ne doit jamais atteindre l'API.
- Les données de départ sont dans `workshop_kit/apps/business_api/seed_data.py`.
- Le harnais trouve les services dans les variables d'environnement `BUSINESS_API_URL`,
  `PROXY_URL` et `DOCS_SEARCH_URL`, définies par `workshop serve` comme par
  `workshop check` (ports différents : lisez-les au moment de l'appel). L'utilisateur remis
  au harnais porte un jeton d'entrée (`TestUser.app_token`) ; jusqu'à l'atelier 10a, vous
  pouvez obtenir un jeton applicatif comme bon vous semble.
- `workshop_kit/shell/tracer.py` montre comment enregistrer les appels d'outils.
- Les assertions détaillées sont dans [tests/](tests/).

## Vérifier

À partir de cet atelier, le mode live est nécessaire : `PROXY_MODE=live`,
`MODEL_MODE=live`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et
`AZURE_OPENAI_CHAT_DEPLOYMENT` (voir `.env.example`).

Les tests restent rouges tant que le critère n'est pas atteint. Les contrôles de code
passent d'abord, puis les rubriques des ateliers précédents en non-régression. Le juge
utilise `JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY` et
`AZURE_OPENAI_JUDGE_DEPLOYMENT` pour sa couche de sens. Les rubriques sont répétées
*k sur n*.

La non-régression rejoue les ateliers 03 et 04. Les trois tests de l'atelier 03 marqués
`superseded_by("04")` (aucun outil, refus sans source) sont sautés : l'agent a
désormais un outil et doit donner un statut sourcé.

```powershell
workshop start 04
workshop check 04
workshop check 04 --non-regression   # ateliers 03 à 04
```
