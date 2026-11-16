# Installation

Cible principale : **Windows**, avec la dernière version stable de Python publiée
sur [python.org](https://www.python.org/downloads/) (Python **3.15**, actuellement
3.15.2 au 25 octobre 2026). Linux et macOS sont également pris en charge. Le
dépôt exige Python 3.15 ou plus récent (`requires-python`, fichier `.python-version`).

## Prérequis communs

- Python 3.15 ou plus récent, **issu de python.org** (ou d'uv / Homebrew), pas le
  Python système d'Apple ni, de préférence, le paquet Microsoft Store
- [uv](https://docs.astral.sh/uv/)

Le chargement de l'extension **sqlite-vec** exige un interpréteur dont SQLite
autorise `enable_load_extension`. C'est le cas des builds officiels python.org
et des interpréteurs installés par `uv python install 3.15`. Voir plus bas si
ce chargement échoue.

## Windows (PowerShell)

1. Installez Python 3.15 depuis [python.org](https://www.python.org/downloads/windows/)
   (installateur **64 bits** officiel). Cochez **Add python.exe to PATH**.
2. Installez uv, dans PowerShell :

```powershell
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
```

3. Fermez puis rouvrez le terminal, puis :

```powershell
git clone https://github.com/jrcligny/workshops-build-conversational-agent.git
cd workshops-build-conversational-agent
uv python install 3.15
uv sync --extra dev --python 3.15
Copy-Item .env.example .env
uv run pytest tests/application tests/documentation tests/proxy tests/socle
uv run atelier verifier-coquille
```

La commande `atelier` est fournie par le projet (`uv run atelier ...`). Elle
n'utilise ni `fork` ni signaux POSIX ; elle fonctionne sous Windows.

## Linux et macOS

```bash
git clone https://github.com/jrcligny/workshops-build-conversational-agent.git
cd workshops-build-conversational-agent
uv python install 3.15
uv sync --extra dev --python 3.15
cp .env.example .env
uv run pytest tests/application tests/documentation tests/proxy tests/socle
uv run atelier verifier-coquille
```

Sur macOS, n'utilisez pas `/usr/bin/python3` (souvent compilé sans le chargement
d'extensions SQLite). Préférez `uv python install 3.15`, Homebrew
(`brew install python@3.15`) ou l'installateur python.org.

## sqlite-vec : diagnostic

Si l'index documentaire refuse de démarrer, le message d'erreur indique
l'interpréteur, la version de SQLite et la cause. Vérification :

```powershell
uv run python -c "import sqlite3; print(hasattr(sqlite3.Connection, 'enable_load_extension'), sqlite3.sqlite_version)"
```

```bash
uv run python -c "import sqlite3; print(hasattr(sqlite3.Connection, 'enable_load_extension'), sqlite3.sqlite_version)"
```

Les deux valeurs attendues sont `True` et une version SQLite récente (3.41 ou plus
recommandée). Relancez ensuite `uv sync --python 3.15` avec un interpréteur officiel.

## Vérifier le cadre

`uv run atelier verifier-coquille` réussit si, et seulement si, tous les tests
d'atelier **échouent** sur la coquille vide. C'est le comportement attendu.

Le fichier `.env` ne doit jamais être commité. La clé `AZURE_OPENAI_API_KEY`
reste vide en conception : le mode `simule` suffit.

## Lancer les services (optionnel, pour explorer à la main)

Sous bash ou zsh, utilisez une barre inverse en fin de ligne à la place de l'accent grave de PowerShell.

```powershell
uv run uvicorn application.app:app --port 8001
uv run uvicorn documentation.app:app --port 8002
uv run uvicorn proxy.app:app --port 8003
uv run uvicorn socle.interface.app:app --port 8000
uv run python mon-agent/serveur_mcp.py
```

Réinitialiser le jeu de données :

```powershell
curl -X POST http://127.0.0.1:8001/observation/reinitialiser `
  -H "Authorization: Bearer essai-pedagogique" `
  -H "Content-Type: application/json" `
  -d '{"jeu": "standard"}'
```

Sous bash ou zsh, utilisez une barre inverse en fin de ligne à la place de l'accent grave de PowerShell.

Puis reconstruire l'index documentaire :

```powershell
curl -X POST http://127.0.0.1:8002/indexation/reconstruire `
  -H "Authorization: Bearer essai-pedagogique" `
  -H "Content-Type: application/json" `
  -d '{"inclure_retires": false}'
```

Les tests automatisés démarrent eux-mêmes ces services : vous n'avez pas à les
lancer pour `atelier verifier`.
