"""Reads the versioned skills catalog (workshop 13). The catalog itself lives in my-agent/skills/."""

from __future__ import annotations

from pathlib import Path

import yaml

from workshop_config import repo_path, settings

MANIFEST_FILE = "manifest.yaml"


def catalog_dir() -> Path:
    return repo_path(settings.skills_dir)


def manifest_path() -> Path:
    return catalog_dir() / MANIFEST_FILE


def load_manifest() -> dict:
    """The manifest as written, every field kept. Its `skills` list holds one entry per skill:
    `id`, `title`, `version` and `path` (read by the tests), plus any field of yours, such as a
    `description` saying when to load the skill: it is what the model sees before loading it."""
    return yaml.safe_load(manifest_path().read_text(encoding="utf-8")) or {}


def skill_folders() -> list[Path]:
    """One folder per skill under my-agent/skills/<id>/ (empty in the shell)."""
    return sorted(p for p in catalog_dir().iterdir() if p.is_dir())
