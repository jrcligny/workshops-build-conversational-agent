# Ateliers

Un dossier par atelier ; le chapitre 11 du livre est découpé en 10a à 10d. Les numéros d'atelier
sont ceux des dossiers, pas ceux des chapitres : le tableau ci-dessous donne la correspondance,
qui suit l'annexe A du livre. Chaque dossier contient :

- `README.md` : le guide de l'étudiant, en français. Il dit ce qu'il faut construire et pourquoi,
  quand c'est réussi, avec des exemples, ce qu'il faut éviter et des pistes ;
- `contrat.md` : le contrat vérifié par les tests (champs de trace, événements, outils,
  rubriques), les étapes pour essayer et la façon de vérifier ;
- `state.yaml` : l'identifiant et le titre de l'atelier ;
- `tests/` : les tests de bout en bout de l'atelier, avec leurs fixtures si besoin.

Lancez toutes les commandes des contrats depuis la racine du dépôt. Préparez d'abord les
environnements d'outillage et de test, qui sont séparés :

```powershell
uv sync --project tooling/cli --locked --python 3.13
uv sync --project tooling/cli --group tests --locked --python 3.13
uv run --project tooling/cli workshop start 03
uv run --project tooling/cli workshop check 03
uv run --project tooling/cli workshop check 07 --non-regression
```

**Mode du modèle.** Le **mode live** est la référence pour tous les ateliers
(`PROXY_MODE=live`, `MODEL_MODE=live`, voir [GETTING_STARTED.md](../GETTING_STARTED.md)).
L'atelier 03 peut se commencer en mode simulé en attendant un accès Azure, mais se valide en
live. À partir de l'atelier 04, le live est indispensable : c'est l'agent qui décide quel
outil appeler, ce que le modèle simulé ne fait pas. Le mode simulé sert à la CI, à
`check-bootstrap` et à `check-inert`.

**Lecture des résultats.** Les faits vérifiables par le code (état de l'application,
journaux, traces, événements) sont contrôlés d'abord. Une rubrique juge ensuite le sens de
la réponse ; elle est rejouée sur des conversations neuves et passe si `JUDGE_K` essais sur
`JUDGE_N` réussissent (3 sur 5 par défaut). Un test marqué `superseded_by("<id>")` est sauté
en non-régression dès que l'atelier vérifié atteint `<id>` : c'est le cas des tests « pas
encore d'outil » de l'atelier 03 à partir de l'atelier 04.

La CLI se trouve dans `tooling/cli/src/workshop_tools/`. Ses commandes de
vérification lancent pytest avec le groupe de dépendances `tests` et la configuration de `tooling/cli/`. Il
n'y a ni projet Python ni environnement partagé à la racine, et `python start.py` n'installe
jamais les dépendances de test. Voir l'[installation](../docs/installation.md).

| Id | Chapitre du livre | Dossier | Sujet |
|---|---|---|---|
| 03 | 3 | [03-system-prompt](03-system-prompt/) | Prompt système et boucle de conversation |
| 04 | 4 | [04-first-tool](04-first-tool/) | Premier outil |
| 05 | 5 | [05-read-tools](05-read-tools/) | Deux outils de lecture |
| 06 | 6 | [06-agent-loop](06-agent-loop/) | Boucle d'agent |
| 07 | 8 | [07-progressive-disclosure](07-progressive-disclosure/) | Découvrir le contexte progressivement |
| 08 | 9 (et 7) | [08-context-compaction](08-context-compaction/) | Compacter le contexte (et garder l'état de la conversation) |
| 09 | 10 | [09-mcp](09-mcp/) | Contrat d'outil et MCP |
| 10a | 11 | [10a-identity](10a-identity/) | Identité et échange de jeton |
| 10b | 11 | [10b-writes](10b-writes/) | Écritures |
| 10c | 11 | [10c-groupings](10c-groupings/) | Regroupements |
| 10d | 11 | [10d-sandboxing](10d-sandboxing/) | Bac à sable |
| 12 | 12 | [12-long-term-memory](12-long-term-memory/) | Mémoire persistante |
| 13 | 13 | [13-document-search](13-document-search/) | Recherche documentaire |
| 14 | 14 | [14-skills](14-skills/) | *Skills* |
| 15 | 15 | [15-read-without-obeying](15-read-without-obeying/) | Lire sans obéir |
| 17 | 16 | [17-evaluation](17-evaluation/) | Observer et évaluer (avec les parcours `routes/`) |
| 18 | 17 | [18-failures](18-failures/) | Pannes et livraison |
| 19 | 18 | [19-specification](19-specification/) | Spécifier un contrôle |

Les chapitres 1 et 2 n'ont pas d'atelier : ils posent le cadre (ce qu'est un agent
conversationnel, pourquoi on le vérifie par répétition). Le chapitre 7 (l'état de la conversation) n'a pas
d'atelier propre : ses critères sont vérifiés par l'atelier 08. Les ateliers ne sont pas renumérotés
d'après le nouveau plan du livre : les numéros 11 et 16 restent libres. La liste complète des tests est
dans [docs/test-inventory.md](../docs/test-inventory.md), et les noms qu'ils lisent sont dans
[docs/interface-contract.md](../docs/interface-contract.md#names-read-by-the-tests).
