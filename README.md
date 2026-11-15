# Workshops — Build a Conversational Agent

Dépôt compagnon des ateliers du livre *De l'assistant à l'agent : anatomie d'un agent conversationnel*.

Il fournit l'environnement et les tests de bout en bout pour réaliser les ateliers (chapitres 3 à 19, le chapitre 10 étant découpé en 10a à 10d). **Il ne contient pas le code de l'agent** : vous construisez le vôtre dans `mon-agent/`, à partir d'une coquille minimale (interface de chat, client de modèle branché sur le proxy, émission de traces, contrat d'interface). La coquille n'inclut ni la boucle conversationnelle ni le *system prompt*.

## Contenu

- `application/` — API métier du fil rouge (FastAPI, SQLite) : commandes, achats, factures, rôles, deux organisations, endpoint d'observation.
- `documentation/` — recherche documentaire (processus séparé) : index SQLite (FTS5 + vecteurs), corpus en `.txt` dans `corpus/`.
- `proxy/` — proxy compatible OpenAI, devant Azure OpenAI plus tard. En conception, seuls les modes **simulé** et **rejoué** sont disponibles. La clé Azure, si elle est un jour configurée, se lit dans une variable d'environnement et n'est jamais versionnée.
- `socle/` — contrat d'interface, traces, client de modèle, interface de chat.
- `tests/atelier-03` … `tests/atelier-19` (dont `atelier-10a` à `atelier-10d`) — critères de réussite. **Ces tests échouent tant que l'atelier n'est pas réalisé** (logique rouge puis vert).
- `tests/application`, `tests/documentation`, `tests/proxy`, `tests/socle` — tests du cadre, qui doivent passer.

## Licence

La licence n'est pas encore fixée. Aucun fichier `LICENSE` n'est publié pour le moment.

## Démarrage rapide

Voir [docs/installation.md](docs/installation.md). En résumé :

```bash
uv sync --extra dev
cp .env.example .env
uv run pytest tests/application tests/documentation tests/proxy tests/socle
uv run atelier verifier-coquille   # succès si tous les tests d'atelier échouent sur la coquille
uv run atelier verifier 03         # reste rouge tant que l'atelier 03 n'est pas fait
```

## Documentation

- [Installation](docs/installation.md)
- [Contrat d'interface](docs/contrat-interface.md)
- [Procédure de validation de l'équipe](docs/validation-equipe.md) (phase B, une fois Azure disponible)
- [Avant de commencer](AVANT-DE-COMMENCER.md)
