"""Typed settings, with no secret by default."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


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
    # Everything a student edits lives in my-agent/. Relative paths resolve against the repository root.
    my_agent_dir: str = "my-agent"
    sandbox_policy_file: str = "my-agent/sandbox/policy.yaml"
    skills_dir: str = "my-agent/skills"
    attachments_dir: str = "my-agent/attachments"

    # Frozen clock of the dataset (Europe/Paris, conventional repository date)
    frozen_clock: str = "2026-03-15T10:00:00"

    compaction_message_threshold: int = 8
    prompt_token_cap: int = 800
    judge_k: int = 3
    judge_n: int = 5
    # Evaluation routes of workshop 17: each route runs on a fresh conversation, k out of n.
    # One run by default: a route is one case among many and the whole set fits in the daily quota.
    route_k: int = 1
    route_n: int = 1
    # Meaning layer of the judge: auto | semantic | structural (see workshop_tests/evaluation/judge.py).
    judge_mode: str = "auto"
    # OpenAI-compatible base URL of the judge model (for example the proxy's /v1) and its bearer token.
    judge_base_url: str = ""
    judge_api_key: str = ""


settings = Settings()


def repo_path(value: str | Path) -> Path:
    """Resolves a configured path: absolute as is, relative against the repository root."""
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path
