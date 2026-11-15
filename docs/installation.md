# Installation

## Prérequis

- Python 3.12 ou plus récent
- [uv](https://docs.astral.sh/uv/)

## Mise en place

```bash
git clone https://github.com/jrcligny/workshops-build-conversational-agent.git
cd workshops-build-conversational-agent
uv sync --extra dev
cp .env.example .env
```

Le fichier `.env` ne doit jamais être commité. La clé `AZURE_OPENAI_API_KEY` reste vide en conception : le mode `simule` suffit.

## Vérifier le cadre

```bash
uv run pytest tests/application tests/documentation tests/proxy tests/socle
uv run atelier verifier-coquille
```

La seconde commande réussit si, et seulement si, tous les tests d'atelier **échouent** sur la coquille vide. C'est le comportement attendu.

## Lancer les services (optionnel, pour explorer à la main)

Dans des terminaux distincts :

```bash
uv run uvicorn application.app:app --port 8001
uv run uvicorn documentation.app:app --port 8002
uv run uvicorn proxy.app:app --port 8003
uv run uvicorn socle.interface.app:app --port 8000
```

Réinitialiser le jeu de données :

```bash
curl -X POST http://127.0.0.1:8001/observation/reinitialiser \
  -H "Authorization: Bearer essai-pedagogique" \
  -H "Content-Type: application/json" \
  -d '{"jeu": "standard"}'
```

Puis reconstruire l'index documentaire :

```bash
curl -X POST http://127.0.0.1:8002/indexation/reconstruire \
  -H "Authorization: Bearer essai-pedagogique" \
  -H "Content-Type: application/json" \
  -d '{"inclure_retires": false}'
```

Les tests automatisés démarrent eux-mêmes ces services : vous n'avez pas à les lancer pour `atelier verifier`.
