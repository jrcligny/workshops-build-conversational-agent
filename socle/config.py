"""Configuration typée, sans secret par défaut."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Reglages(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    proxy_mode: str = "simule"
    modele_mode: str = "simule"

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_deploiement_chat: str = ""
    azure_openai_deploiement_juge: str = ""
    azure_openai_deploiement_embeddings: str = ""
    azure_openai_deploiement_repli: str = ""
    azure_openai_deploiement_reclassement: str = ""

    secret_jetons: str = "changez-moi-en-local"
    jeton_observation: str = "essai-pedagogique"
    quota_jetons_par_jour: int = 200000
    quota_requetes_par_jour: int = 500

    application_db: str = "application.db"
    documentation_db: str = "documentation.db"
    traces_dir: str = "traces"
    mon_agent_dir: str = "mon-agent"

    # Horloge figée du jeu de données (Europe/Paris, date conventionnelle du dépôt)
    horloge_figee: str = "2026-03-15T10:00:00"

    seuil_compaction_messages: int = 8
    plafond_prompt_tokens: int = 800
    juge_k: int = 3
    juge_n: int = 5


reglages = Reglages()
