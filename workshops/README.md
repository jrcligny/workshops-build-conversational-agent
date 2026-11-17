# Ateliers

Un atelier par chapitre du livre, de 3 à 17 : le numéro de l'atelier est celui du chapitre
(annexe A du livre). Le chapitre 8 (la mémoire de travail) n'a pas d'atelier
propre : l'état de conversation qu'il décrit est exercé à l'atelier 10. Chaque dossier contient :

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
uv run --project tooling/cli workshop check 09 --non-regression
uv run --project tooling/cli workshop check 07 --etape ecritures
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

| Id | Dossier | Sujet | Étapes (`--etape`) |
|---|---|---|---|
| 03 | [03-system-prompt](03-system-prompt/) | Prompt système et boucle de conversation | |
| 04 | [04-first-tool](04-first-tool/) | Premier outil | |
| 05 | [05-agent-loop](05-agent-loop/) | Outils de lecture et boucle d'agent | `outils`, `boucle` |
| 06 | [06-mcp-server](06-mcp-server/) | Serveur d'outils MCP et regroupements | `serveur`, `regroupements` |
| 07 | [07-acting-rights](07-acting-rights/) | Identité, écritures et confinement | `identite`, `ecritures`, `confinement` |
| 09 | [09-progressive-disclosure](09-progressive-disclosure/) | Divulgation progressive sur l'outil générique | |
| 10 | [10-context-compaction](10-context-compaction/) | État de conversation et compaction | |
| 11 | [11-no-memory](11-no-memory/) | Aucune mémoire, dite explicitement | |
| 12 | [12-document-search](12-document-search/) | Recherche documentaire | |
| 13 | [13-skills](13-skills/) | *Skills* | |
| 14 | [14-read-without-obeying](14-read-without-obeying/) | Lire sans obéir | |
| 15 | [15-evaluation](15-evaluation/) | Traces et évaluation (avec les parcours `routes/`) | |
| 16 | [16-failures](16-failures/) | Pannes | |
| 17 | [17-specification](17-specification/) | Spécifier un contrôle | |
| bonus | [bonus-preference-memory](bonus-preference-memory/) | Mémoire de préférences (hors parcours) | |

Les chapitres 1 et 2 n'ont pas d'atelier : ils posent le cadre (ce qu'est un agent
conversationnel, pourquoi on le vérifie par répétition). Le chapitre 8 n'en a pas non plus. Un
atelier en plusieurs étapes se vérifie étape par étape avec `--etape`, puis en entier.
L'atelier bonus met en œuvre l'option écartée par le chapitre 11 (une mémoire de préférences) :
ses tests contredisent ceux de l'atelier 11, et `--non-regression` ne le rejoue jamais. La
liste complète des tests est dans [docs/test-inventory.md](../docs/test-inventory.md), et les noms
qu'ils lisent sont dans [docs/interface-contract.md](../docs/interface-contract.md#names-read-by-the-tests).
