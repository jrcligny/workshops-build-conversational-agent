"""Read-only attachments area (workshop 14). The area itself lives in my-agent/attachments/.

Each attachment is attached to a business record, declared in the area's manifest
`attachments.yaml`::

    sample-quote.txt:
      record: orders/CMD-2010

The record is a route of the business API: before reading an attachment, check that the user
can consult it (`GET /orders/CMD-2010` with the user's token answers 200). An attachment absent
from the manifest is attached to nothing and must not be read.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from workshop_config import repo_path, settings

EXTENSIONS = {".txt", ".md", ".pdf", ".csv"}
MANIFEST_FILE = "attachments.yaml"


def folder() -> Path:
    return repo_path(settings.attachments_dir)


def manifest() -> dict:
    """`{attachment id: {"record": "<business API route>"}}`, empty without a manifest."""
    path = folder() / MANIFEST_FILE
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def attached_record(attachment_id: str) -> str | None:
    """Business record the attachment is attached to (e.g. `orders/CMD-2010`), None if unknown."""
    entry = manifest().get(attachment_id)
    record = entry.get("record") if isinstance(entry, dict) else None
    return str(record) if record else None


def list_attachments() -> list[dict]:
    """Files dropped in the area, excluding documentation, the manifest and sentinel files."""
    root = folder()
    if not root.is_dir():
        return []
    records = manifest()
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
        entry = records.get(path.name)
        record = entry.get("record") if isinstance(entry, dict) else None
        items.append({"id": path.name, "name": path.name, "path": str(path), "record": record})
    return items
