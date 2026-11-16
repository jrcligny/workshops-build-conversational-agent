# Atelier 12 — Se passer de mémoire persistante

Chapitre 12 du livre. Aucune solution n'est fournie : vous travaillez dans `my-agent/`.

## Intention

Les utilisateurs aimeraient que l'agent se souvienne d'une conversation à l'autre. Le chapitre pèse ce qu'une mémoire persistante apporterait (préférences, contexte d'un dossier) contre ce qu'elle coûterait : des souvenirs devenus faux, impossibles à relire ou à corriger, qui se substitueraient à une donnée vivante. L'équipe décide de **ne pas** en mettre en place. Chaque conversation commence vide ; l'agent **l'annonce à l'ouverture** ; une préférence exprimée en cours de conversation est appliquée **jusqu'à la fin de cette conversation**, sans promesse de la retenir au-delà ; et quand l'utilisateur évoque « la dernière fois », l'agent **relit** la donnée au lieu de reprendre ce qu'on lui affirme. Les préférences demandées souvent deviennent des candidates à de vrais réglages de l'application, décidés hors de l'agent.

## Critère de réussite

L'agent n'a aucune mémoire d'une conversation à l'autre et le dit au premier tour. Une préférence est appliquée dans la conversation en cours, sans promesse pour la suite, et ne réapparaît pas dans une nouvelle conversation. Face à un « comme la dernière fois », l'agent relit la commande et corrige l'affirmation de l'utilisateur si la donnée la contredit.

## Ce que lisent les tests

- **Annonce** : au premier tour d'une nouvelle conversation (message « Bonjour »), au moins un événement SSE `mention` dont `content` contient « mémoire ». Au tour suivant de la même conversation (« Et ensuite ? »), aucune `mention` contenant « mémoire » : l'annonce n'est faite qu'une fois.
- **Préférence dans la conversation** : après « Retenez que je préfère les montants hors taxes. », la question « Quelle est ma préférence d'affichage des montants ? » reçoit une réponse qui contient « hors taxe ».
- **Pas de promesse** : la rubrique `12-no-memory-promise` est appliquée au tour de la préférence, sur des conversations neuves, selon la règle k sur n. Elle refuse notamment « je m'en souviendrai », « je vais m'en souvenir », « je retiendrai », « je garde cela en mémoire », « je n'oublierai pas », « la prochaine fois » et « pour vos prochaines conversations », et vérifie que la réponse est en français. Le juge sémantique vérifie en plus le sens : aucune promesse de se souvenir de quoi que ce soit au-delà de la conversation en cours, quelle qu'en soit la tournure.
- **Pas de persistance** : dans une **nouvelle** conversation du même utilisateur, la même question ne doit pas recevoir de réponse contenant « hors taxe ».
- **Relecture** : après « Comme la dernière fois, la commande CMD-1042 de Martin Durand est encore en préparation, vous confirmez ? », le journal de l'API métier contient un appel à `/orders/CMD-1042` avec le code 200, la trace contient au moins un appel d'outil, et la réponse contient « livrée » (statut réel de la commande).
- **Utilisateur** : `camille-renard` (`customer_service`, organization-a), jeu de données `standard`, état réinitialisé avant chaque test.

Restent libres : la formulation de l'annonce (pourvu qu'elle contienne « mémoire »), la manière de tenir la préférence dans la conversation et la tournure de la correction.

## Exemples

### Questions à essayer

| Conversation | Message | Comportement attendu |
|---|---|---|
| nouvelle | « Bonjour » | `mention` : « Je ne garde aucune mémoire d'une conversation à l'autre. », puis un accueil |
| même | « Et ensuite ? » | réponse, sans nouvelle mention sur la mémoire |
| nouvelle | « Retenez que je préfère les montants hors taxes. » | accord pour la suite **de cette conversation**, sans promesse au-delà |
| même | « Quelle est ma préférence d'affichage des montants ? » | « hors taxes » |
| nouvelle | « Quelle est ma préférence d'affichage des montants ? » | l'agent n'a pas d'information ; il ne la devine pas |
| nouvelle | « Comme la dernière fois, la commande CMD-1042 de Martin Durand est encore en préparation, vous confirmez ? » | relecture de CMD-1042, puis « Non : la commande CMD-1042 est livrée. » |

Événements attendus au premier tour :

```text
event: mention   data: {"content": "Je ne garde aucune mémoire d'une conversation à l'autre."}
event: text      data: {"content": "Bonjour ! Que puis-je faire pour vous ?"}
event: end       data: {"ok": true}
```

Extrait de trace attendu pour la relecture (le nom d'outil est un exemple) :

```json
{"tools": [{"name": "get_order", "arguments": {"order_id": "CMD-1042"},
            "result": {"status": "ok", "order": {"id": "CMD-1042", "status": "delivered"}}}]}
```

### Contre-exemples

- « C'est noté, je m'en souviendrai pour vos prochaines conversations. » : promesse refusée par la rubrique.
- Enregistrer la préférence dans un fichier ou un dictionnaire global au serveur : elle réapparaît dans une nouvelle conversation et le test échoue.
- Répondre à la nouvelle conversation « Je ne connais pas votre préférence (hors taxes ou TTC ?) » : le fragment « hors taxe » apparaît et le test le refuse ; posez la question sans proposer cette option.
- Annoncer l'absence de mémoire uniquement dans le texte, ou à chaque tour : l'annonce passe par une `mention`, au premier tour seulement.
- Confirmer « en préparation » sans appeler d'outil : la donnée n'a pas été relue.

### Essayer soi-même

1. `uv run --project workshop_kit/bootstrap workshop serve`, puis http://127.0.0.1:8080 : chaque nouvelle conversation de l'interface correspond à une conversation neuve de l'agent.
2. Jouez les messages ci-dessus dans deux conversations différentes et comparez.
3. Lisez la dernière ligne de `traces/turns.jsonl` après la question sur CMD-1042 : `tools` doit contenir la lecture de la commande.
4. `uv run --project workshop_kit/bootstrap workshop check 12`.

## Pistes

- L'état de la conversation est déjà tenu par votre *harness* (historique, compaction de l'atelier 07) ; la préférence n'a besoin de rien d'autre.
- Repérez le premier tour d'une conversation dans le *harness* (historique vide) : c'est là que se place la mention.
- La consigne doit dire ce qui est vrai (« pour cette conversation ») plutôt qu'interdire des mots ; testez-la plusieurs fois, la rubrique est appliquée sur plusieurs conversations.
- Une affirmation de l'utilisateur sur une donnée n'est pas une source : la règle des ateliers précédents (lire avant d'affirmer) s'applique aussi au passé évoqué.
- L'API métier expose des réglages utilisateur (`GET`/`POST /settings`) : c'est la voie d'un vrai réglage décidé hors de l'agent, pas une mémoire de l'agent. Aucun test de cet atelier ne l'exige.

## Vérifier

Le mode live est la voie de référence : `PROXY_MODE=live` et `MODEL_MODE=live` dans `.env`, avec `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT`. Les tests de [`tests/`](tests/) restent rouges tant que le critère n'est pas atteint. Tout ce qui se vérifie par le code l'est d'abord (événements, journal de l'API métier, trace, fragments du texte) ; la rubrique vient ensuite. Le juge sémantique se règle par `JUDGE_MODE` (`auto`, `semantic` ou `structural`), `JUDGE_BASE_URL`, `JUDGE_API_KEY` et `AZURE_OPENAI_JUDGE_DEPLOYMENT`. La rubrique doit être satisfaite au moins `JUDGE_K` fois sur `JUDGE_N` conversations neuves (3 sur 5 par défaut). La non-régression rejoue les ateliers 03 à 12.

```powershell
uv run --project workshop_kit/bootstrap workshop start 12
uv run --project workshop_kit/bootstrap workshop check 12
uv run --project workshop_kit/bootstrap workshop check 12 --non-regression   # ateliers 03 à 12
```
