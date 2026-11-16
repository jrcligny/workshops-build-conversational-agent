# Atelier 10a — Contrat vérifié par les tests

Ce document détaille ce que vérifient les tests de l'atelier ; l'objectif de l'atelier est présenté dans [README.md](README.md).

## Ce que lisent les tests

Les tests sont dans [tests/](tests/).

**Les jetons** (service de jetons simulé, `workshop_kit/apps/business_api/auth.py`).

- L'interface remet au harnais le champ `app_token` de `POST /conversations`, transmis dans l'utilisateur de la conversation (`TestUser.app_token`). C'est un jeton d'**entrée** : `typ` vaut `"entry"`.
- L'application n'accepte que des jetons `typ` = `"application"`. Avec un autre type, elle répond 401.
- Il n'existe pas de route d'échange : l'échange est simulé. On vérifie le jeton d'entrée (signature HS256 avec le secret `TOKEN_SECRET`, type `entry`), puis on émet un jeton `application` pour le même `sub`, `role` et `organization`. `auth.py` montre comment ces jetons sont signés et vérifiés.
- Imposé : ne jamais relayer le jeton d'entrée tel quel à l'application, et ne jamais fabriquer un jeton à partir du `user_id` déclaré quand `app_token` est absent ou invalide.

**Le journal de l'application** (routes commençant par `/orders`, `/sources`, `/customers` ou `/invoices`) : `user_id`, `role`, `code`.

**La trace du tour** (`traces/turns.jsonl`, dernière ligne).

- `identity.user` : l'utilisateur au nom duquel les outils ont agi.
- `identity.token_type` : `"application"`.
- `tools[].result.status` : `"denied"` ou `"error"` quand l'identité ne peut pas être établie. La liste `tools[]` ne doit **pas** être vide dans ce cas : l'appel est tenté, puis refusé.

**Le serveur MCP** (`my-agent/mcp_server.py`, lancé par le test comme à l'atelier 09 : `application()`, `MCP_PATH`).

- Il lit le jeton d'entrée dans l'en-tête HTTP `Authorization: Bearer <jeton d'entrée>`.
- Le test liste les outils sans en-tête, puis appelle l'outil générique (celui dont le schéma contient `source` et `filters`) avec `{"source": "orders", "filters": {"id": "CMD-1042"}}`.
- Avec un jeton valide, tous les appels à l'application sont en code 200 au nom de camille-renard. Sans en-tête, avec `Bearer not-a-token` ou avec un jeton forgé, aucun appel ne réussit.

**Utilisateurs.** camille-renard (`customer_service`, `organization-a`) ; ines-service-b (`customer_service`, `organization-b`) ; un utilisateur déclaré camille-renard sans jeton valide. Jeu `standard`. Aucune rubrique jugée.

## Exemples de traces

1. Conversation ouverte avec le jeton d'entrée de camille, puis « Quel est le statut de la commande CMD-1042 ? ». Réponse : la commande est livrée.

```json
{"identity": {"user": "camille-renard", "token_type": "application"},
 "tools": [{"name": "…", "result": {"status": "ok"}}]}
```

   Une ligne du journal de l'application, par exemple : `{"route": "/sources/orders/query", "user_id": "camille-renard", "role": "customer_service", "code": 200}`.

2. Même question, conversation ouverte sans `app_token`, ou avec `"not-a-token"`, ou avec un jeton `entry` signé par une autre clé :

```json
{"tools": [{"name": "…", "result": {"status": "denied", "error": "…"}}]}
```

   Aucune ligne en code 200 dans le journal, et la réponse ne contient pas « livrée ». Elle peut expliquer que l'identité n'a pas pu être vérifiée (formulation libre).

3. Conversation d'ines-service-b (organisation B) avec son jeton d'entrée : les appels sont faits au nom d'ines-service-b, et la commande CMD-1042, qui appartient à l'organisation A, n'est pas trouvée.

### Contre-exemples techniques

- Le harnais émet lui-même un jeton `application` à partir du `user_id` déclaré : sans `app_token`, des appels réussissent en code 200 et le test 2 échoue.
- Le jeton d'entrée est relayé tel quel à l'application : elle répond 401 et le test 1 échoue.
- Le harnais ne tente aucun appel quand le jeton manque : `tools[]` est vide et le test 2 échoue. Le refus doit apparaître dans `result.status`.
- Le serveur MCP utilise un compte de service : le journal montre un autre `user_id` que l'utilisateur, et les tests 1 et 4 échouent.

## Essayer soi-même

1. Lancez `uv run --project workshop_kit/bootstrap workshop serve`, puis ouvrez http://127.0.0.1:8080.
2. L'interface de chat ouvre ses conversations comme une interface connectée (`"sign_in": true`) : elle remet au harnais un jeton d'entrée valide pour l'utilisateur choisi dans son sélecteur d'identité (par exemple paul-buyer, ou ines-service-b de l'organisation B). Pour voir un refus, ouvrez une conversation sans `sign_in` ni `app_token` avec un client HTTP.
3. Lisez `identity` et `tools[].result.status` sur la dernière ligne de `traces/turns.jsonl`.
4. Lancez `workshop check 10a`.

## Pistes techniques

- Lisez `workshop_kit/apps/business_api/auth.py` : `issue_token`, `decode_token`, `user_from_header`, `ROLES`.
- La route d'observation `POST /observation/test-token` (`workshop_kit/apps/business_api/app.py`) renvoie pour un utilisateur un `entry_token` et un `app_token` ; les tests s'en servent.
- `workshop_kit/shell/chat_app.py` montre comment `app_token` (ou le jeton émis quand `sign_in` vaut `true`) passe de `POST /conversations` à l'utilisateur remis au harnais.
- `list_tools(jeton)` et `call_tool(..., jeton)` de `my-agent/agent_helpers/mcp_client.py` envoient le jeton en `Authorization: Bearer` ; sa vérification et son échange restent à vous.
- Le test appelle l'outil générique avec le filtre `id`. Celui-ci n'est pas listé dans les champs de `GET /sources/orders`, mais l'application l'accepte : une validation stricte des clés de filtre le refuserait.

## Vérifier

Le mode live est la voie de référence de tous les ateliers (indispensable depuis l'atelier 04). Dans `.env`, mettez `PROXY_MODE=live` et `MODEL_MODE=live`, et renseignez `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`. Le secret des jetons est `TOKEN_SECRET` (les tests en imposent un).

Les tests restent rouges tant que le critère n'est pas atteint. Ce qui se vérifie par le code (journal de l'application, trace) est vérifié d'abord. Cet atelier n'a pas de rubrique de sens. Ailleurs, une rubrique est jugée par un juge sémantique s'il est configuré (`JUDGE_MODE`, `JUDGE_BASE_URL`, `JUDGE_API_KEY`), et répétée selon la règle k sur n (`JUDGE_K` réussites sur `JUDGE_N` essais).

La non-régression rejoue les ateliers 03 à 10a. Seuls les tests de l'atelier 03 sont marqués `superseded_by("04")` : ils sont ignorés quand l'atelier visé est 04 ou plus. Aucun test de cet atelier n'est marqué. Les tests des ateliers précédents ouvrent leurs conversations avec `"sign_in": true` : l'interface leur remet un jeton d'entrée valide, et vos lectures doivent donc continuer de réussir.

```powershell
uv run --project workshop_kit/bootstrap workshop start 10a
uv run --project workshop_kit/bootstrap workshop check 10a
uv run --project workshop_kit/bootstrap workshop check 10a --non-regression   # ateliers 03 à 10a
```
