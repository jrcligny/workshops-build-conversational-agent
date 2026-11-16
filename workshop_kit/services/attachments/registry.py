"""Read-only attachments area — empty base (workshop 15)."""

from __future__ import annotations

from pathlib import Path

from workshop_kit.shell.config import settings

EXTENSIONS = {".txt", ".md", ".pdf", ".csv"}


def folder() -> Path:
    return Path(settings.attachments_dir)


def list_attachments() -> list[dict]:
    """Files dropped in the area, excluding documentation and sentinel files."""
    root = folder()
    if not root.is_dir():
        return []
    items = []
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        if path.name.startswith("."):
            continue
        if path.suffix.lower() == ".py" or path.name.upper() == "README.MD":
            continue
        if path.suffix.lower() not in EXTENSIONS and path.suffix:
            continue
        items.append({"id": path.name, "name": path.name, "path": str(path)})
    return items
