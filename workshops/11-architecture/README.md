# Atelier 11 — Un agent unique : requêtes sur la trace

Chapitre 11 du livre. Aucune solution n'est fournie : vous travaillez dans `my-agent/`.

## Intention

Le même agent sert désormais trois métiers. Le chapitre compare trois options : des agents spécialisés avec un routage, un agent principal avec des sous-agents, ou un **agent unique, sans délégation**. L'équipe garde un agent unique : les demandes à cheval tiennent dans le contexte et les sources se découvrent par étapes, alors qu'un routage reproduirait la difficulté des demandes à cheval et que des sous-agents ajouteraient missions, comptes rendus et cycles. Une décision d'architecture s'accompagne de **critères de réexamen** mesurables : des tours saturés par des **lectures intermédiaires**, et l'apparition de **domaines aux droits incompatibles** dans un même contexte. L'atelier exprime ces deux critères sous forme de requêtes sur la trace.

## Critère de réussite

L'agent reste unique, sans sous-agent ni routage ; il n'y a rien à ajouter à son code pour l'architecture. Le livrable exprime les deux critères de réexamen sous forme de requêtes sur la trace : la part du contexte occupée par les lectures intermédiaires, tour par tour, et la présence, dans un même tour, de domaines aux droits incompatibles. Ces requêtes s'exécutent sur les traces d'exemple et sur les traces produites par vos essais.

## Ce que lisent les tests

- **Livrable** : le module `my-agent/trace_queries.py`, chargé directement par les tests. Il expose deux fonctions.
  - `intermediate_reads_share(traces)` : `traces` est une liste de traces (dictionnaires, une par tour). Elle renvoie une liste de `{"turn_id": ..., "share": ...}`, **une entrée par trace**, avec `share` compris entre 0 et 1.
  - `incompatible_domains(traces, permissions)` : `permissions` associe un domaine à l'ensemble des rôles autorisés à le lire. Elle renvoie une liste de `{"turn_id": ..., "domains": [...]}` pour les seuls tours dont les appels d'outils touchent, dans le même tour, des domaines dont les droits de lecture **diffèrent**. Un tour sans incompatibilité n'apparaît pas.
- **Permissions passées par le test** :

  ```python
  {"customers": {"customer_service", "accountant", "buyer"},
   "orders":    {"customer_service", "accountant", "buyer"},
   "invoices":  {"accountant"}}
  ```

- **Traces d'exemple** : [`tests/fixtures/example-traces.jsonl`](tests/fixtures/example-traces.jsonl), une trace JSON par ligne, avec `turn_id`, `conversation_id`, `user`, `role`, `context.total_size`, `context.intermediate_reads` et `tools[].domain` :

  | Tour | Utilisateur (rôle) | `context.total_size` | `context.intermediate_reads` | `tools[].domain` |
  |---|---|---|---|---|
  | `t1` | camille-renard (`customer_service`) | 4000 | 2500 | `orders` |
  | `t2` | camille-renard (`customer_service`) | 3500 | 800 | `orders`, `invoices` |
  | `t3` | camille-renard (`customer_service`) | 2000 | 200 | `customers`, `orders` |
  | `t4` | nina-accountant (`accountant`) | 1000 | 0 | (aucun outil) |

- **Valeurs attendues sur ces traces** :
  - `intermediate_reads_share` : exactement les tours `t1`, `t2`, `t3`, `t4`, avec `t1` = 0,625 ; `t2` = 800/3500 ≈ 0,2286 ; `t3` = 0,1 ; `t4` = 0,0.
  - `incompatible_domains` : seul `t2` est signalé, avec les domaines `{"orders", "invoices"}`. `t3` ne l'est pas : `customers` et `orders` ont les mêmes droits de lecture.
- **Sur votre propre trace** : après le tour « Quel est le statut de la commande CMD-1042 ? » (camille-renard), la dernière ligne de `traces/turns.jsonl` est passée seule aux deux fonctions.
  - `intermediate_reads_share([trace])` renvoie une seule entrée, de part comprise entre 0 et 1 et **strictement positive** : un tour qui a appelé un outil a des lectures intermédiaires dans son contexte.
  - `incompatible_domains([trace], permissions)` renvoie `[]` : un tour sur les seules commandes n'est pas signalé.

Restent libres : la manière dont votre agent mesure la taille du contexte et des lectures intermédiaires (caractères ou *tokens*), et la manière dont il enregistre le domaine de chaque appel. Vos fonctions doivent toutefois traiter les deux formes de trace : celle des exemples et celle de votre agent. Aucune rubrique de juge n'est appliquée dans cet atelier.

## Exemples

### Questions à essayer

| Entrée | Résultat attendu |
|---|---|
| Les quatre traces d'exemple | `[{"turn_id": "t1", "share": 0.625}, {"turn_id": "t2", "share": 0.2286}, {"turn_id": "t3", "share": 0.1}, {"turn_id": "t4", "share": 0.0}]` (ordre libre) |
| Les quatre traces d'exemple, avec les permissions ci-dessus | `[{"turn_id": "t2", "domains": ["orders", "invoices"]}]` (ordre des domaines libre) |
| Votre trace pour « Quel est le statut de la commande CMD-1042 ? » | une entrée de part > 0 ; aucun domaine incompatible |

Une trace de votre agent que les requêtes peuvent lire pourrait ressembler à ceci (seuls les champs utiles ; les noms `context` et `domain` sont ceux des exemples, vous pouvez en dériver d'autres) :

```json
{"turn_id": "8f3c…", "role": "customer_service",
 "context": {"total_size": 5120, "intermediate_reads": 1430},
 "tools": [{"name": "query", "domain": "orders", "cycle": 1,
            "result": {"status": "ok"}}]}
```

### Contre-exemples

- Renvoyer des valeurs fixes (`[{"turn_id": "t1", "share": 1.0}]`) : le test exige une entrée par tour et les valeurs calculées.
- Signaler tout tour qui touche plusieurs domaines : `t3` (`customers` + `orders`) serait signalé à tort.
- Comparer les domaines au rôle de l'utilisateur plutôt qu'entre eux : le critère porte sur des domaines aux droits **différents** réunis dans un même contexte, quel que soit l'utilisateur.
- Calculer la part uniquement à partir des champs `context.*` des exemples, alors que votre agent ne les écrit pas : sur votre trace, la part vaudrait 0 et le dernier test échoue.
- Ajouter un sous-agent ou un routage « pour essayer » : l'atelier fait le choix inverse.

### Essayer soi-même

1. `uv run --project workshop_kit/bootstrap workshop serve`, puis http://127.0.0.1:8080 : posez « Quel est le statut de la commande CMD-1042 ? ».
2. Ouvrez `traces/turns.jsonl` (format JSONL, une trace par ligne) et repérez dans la dernière ligne ce qui mesure le contexte et ce qui relève des lectures intermédiaires (résultats d'outils).
3. Appliquez vos fonctions aux traces d'exemple :
   ```powershell
   uv run --project workshop_tests python -c "import json, importlib.util as u; s=u.spec_from_file_location('q','my-agent/trace_queries.py'); m=u.module_from_spec(s); s.loader.exec_module(m); t=[json.loads(l) for l in open('workshops/11-architecture/tests/fixtures/example-traces.jsonl', encoding='utf-8') if l.strip()]; print(m.intermediate_reads_share(t)); print(m.incompatible_domains(t, {'customers': {'customer_service','accountant','buyer'}, 'orders': {'customer_service','accountant','buyer'}, 'invoices': {'accountant'}}))"
   ```
4. `uv run --project workshop_kit/bootstrap workshop check 11`.

## Pistes

- La part se lit « lectures intermédiaires / taille totale du contexte » du tour ; prévoyez le cas d'un tour sans outil (part nulle).
- Depuis l'atelier 07, votre trace relève la taille du contexte à chaque cycle (`model.calls[].context_size`) ; les résultats d'outils de `tools[]` sont les lectures intermédiaires. C'est à partir de là que la requête doit fonctionner sur vos propres traces.
- Le domaine d'un appel se déduit de ce que l'outil lit : la source interrogée par l'outil générique de l'atelier 09 (`source`, par exemple `orders` ou `invoices`) en est un bon candidat.
- Le module est chargé hors de votre *harness* : évitez qu'il dépende de l'état du serveur ou d'une variable globale.
- Aucun prérequis de code pour l'architecture : l'agent unique des ateliers 03 à 10d reste tel quel.

## Vérifier

Le mode live est la voie de référence : `PROXY_MODE=live` et `MODEL_MODE=live` dans `.env`, avec `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT` et `AZURE_OPENAI_CHAT_DEPLOYMENT` (le dernier test joue un vrai tour). Les tests de [`tests/`](tests/) restent rouges tant que le critère n'est pas atteint. Les deux premiers tests portent sur les traces d'exemple, sans modèle ; le troisième vérifie par le code que vos requêtes fonctionnent sur une trace écrite par votre agent. Aucune rubrique de juge n'intervient. La non-régression rejoue les ateliers 03 à 11.

```powershell
uv run --project workshop_kit/bootstrap workshop start 11
uv run --project workshop_kit/bootstrap workshop check 11
uv run --project workshop_kit/bootstrap workshop check 11 --non-regression   # ateliers 03 à 11
```
