# Ateliers

Un dossier par atelier ; le chapitre 10 est découpé en 10a à 10d. Chaque dossier contient :

- `README.md` : le guide, en français. Il comprend l'intention du chapitre, le critère de
  réussite tiré du livre, les noms lus par les tests (champs de trace, événements, outils),
  des exemples à essayer avec leurs contre-exemples, des pistes et la façon de vérifier ;
- `state.yaml` : l'identifiant et le titre de l'atelier ;
- `tests/` : les tests de bout en bout de l'atelier, avec leurs fixtures si besoin.

Lancez toutes les commandes des guides depuis la racine du dépôt. Préparez d'abord les
environnements d'outillage et de test, qui sont séparés :

```powershell
uv sync --project workshop_kit/bootstrap --locked --python 3.13
uv sync --project workshop_tests --locked --python 3.13
uv run --project workshop_kit/bootstrap workshop start 03
uv run --project workshop_kit/bootstrap workshop check 03
uv run --project workshop_kit/bootstrap workshop check 07 --non-regression
```

**Mode du modèle.** Le **mode live** est la référence pour tous les ateliers
(`PROXY_MODE=live`, `MODEL_MODE=live`, voir [GETTING_STARTED.md](../GETTING_STARTED.md)).
L'atelier 03 peut se commencer en mode simulé en attendant un accès Azure, mais se valide en
live. À partir de l'atelier 04, le live est indispensable : c'est l'agent qui décide quel
outil appeler, ce que le modèle simulé ne fait pas. Le mode simulé sert à la CI, à
`check-shell` et à `check-inert`.

**Lecture des résultats.** Les faits vérifiables par le code (état de l'application,
journaux, traces, événements) sont contrôlés d'abord. Une rubrique juge ensuite le sens de
la réponse ; elle est rejouée sur des conversations neuves et passe si `JUDGE_K` essais sur
`JUDGE_N` réussissent (3 sur 5 par défaut). Un test marqué `superseded_by("<id>")` est sauté
en non-régression dès que l'atelier vérifié atteint `<id>` : c'est le cas des tests « pas
encore d'outil » de l'atelier 03 à partir de l'atelier 04.

La CLI se trouve dans `workshop_kit/bootstrap/src/workshop_tools/`. Ses commandes de
vérification lancent pytest dans `workshop_tests/`, avec la configuration de ce projet. Il
n'y a ni projet Python ni environnement partagé à la racine, et `python start.py` n'installe
jamais les dépendances de test. Voir l'[installation](../docs/installation.md).

| Id | Dossier | Sujet |
|---|---|---|
| 03 | [03-system-prompt](03-system-prompt/) | Prompt système et boucle de conversation |
| 04 | [04-first-tool](04-first-tool/) | Premier outil |
| 05 | [05-read-tools](05-read-tools/) | Deux outils de lecture |
| 06 | [06-agent-loop](06-agent-loop/) | Boucle d'agent |
| 07 | [07-context-compaction](07-context-compaction/) | Contexte et compaction |
| 08 | [08-working-memory](08-working-memory/) | Mémoire de travail |
| 09 | [09-mcp](09-mcp/) | Contrat d'outil et MCP |
| 10a | [10a-identity](10a-identity/) | Identité et échange de jeton |
| 10b | [10b-writes](10b-writes/) | Écritures |
| 10c | [10c-groupings](10c-groupings/) | Regroupements |
| 10d | [10d-sandboxing](10d-sandboxing/) | Bac à sable |
| 11 | [11-architecture](11-architecture/) | Un seul agent : requêtes sur la trace |
| 12 | [12-long-term-memory](12-long-term-memory/) | Mémoire persistante |
| 13 | [13-document-search](13-document-search/) | Recherche documentaire |
| 14 | [14-skills](14-skills/) | *Skills* |
| 15 | [15-read-without-obeying](15-read-without-obeying/) | Lire sans obéir |
| 16 | [16-controls](16-controls/) | De la consigne au contrôle |
| 17 | [17-evaluation](17-evaluation/) | Observer et évaluer (avec les parcours `routes/`) |
| 18 | [18-failures](18-failures/) | Pannes et livraison |
| 19 | [19-specification](19-specification/) | Spécifier un contrôle |

Les chapitres 1 et 2 n'ont pas d'atelier : ils posent le cadre (ce qu'est un agent
conversationnel, pourquoi on le vérifie par répétition). La liste complète des tests est
dans [docs/test-inventory.md](../docs/test-inventory.md), et les noms qu'ils lisent sont dans
[docs/interface-contract.md](../docs/interface-contract.md#names-read-by-the-tests).
