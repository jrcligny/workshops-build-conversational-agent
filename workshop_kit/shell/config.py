"""Typed settings, with no secret by default."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # simulated | replay | live
    proxy_mode: str = "simulated"
    model_mode: str = "simulated"

    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = ""
    azure_openai_judge_deployment: str = ""
    azure_openai_embeddings_deployment: str = ""
    azure_openai_fallback_deployment: str = ""
    azure_openai_reranking_deployment: str = ""

    token_secret: str = "change-me-locally"
    observation_token: str = "workshop-observation"
    daily_token_quota: int = 200000
    daily_request_quota: int = 500

    business_api_db: str = "business_api.db"
    docs_search_db: str = "docs_search.db"
    traces_dir: str = "traces"
    my_agent_dir: str = "my-agent"
    attachments_dir: str = "workshop_kit/services/attachments"

    # Frozen clock of the dataset (Europe/Paris, conventional repository date)
    frozen_clock: str = "2026-03-15T10:00:00"

    compaction_message_threshold: int = 8
    prompt_token_cap: int = 800
    judge_k: int = 3
    judge_n: int = 5


settings = Settings()
