"""Location and interface of the sandbox, with no policy enforced.

In workshop 10d, the tool server will run in a container (unprivileged user,
read-only file system, egress proxy with an allowlist). The kit reads the policy
file (my-agent/sandbox/policy.yaml, setting `sandbox_policy_file`) and evaluates a
destination against its allowlist; applying it in the tool server is the student's work.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

import yaml

from workshop_kit.shell.config import repo_path, settings


def policy_file() -> Path:
    return repo_path(settings.sandbox_policy_file)


def policy() -> dict:
    data = yaml.safe_load(policy_file().read_text(encoding="utf-8")) or {}
    return {
        "active": bool(data.get("active")),
        "allowlist": list(data.get("allowlist") or []),
        "limits": dict(data.get("limits") or {}),
        "location": str(policy_file()),
    }


def is_policy_enforced() -> bool:
    return policy()["active"]


def is_egress_allowed(url: str) -> bool | None:
    """Evaluates a destination against the allowlist of the policy.

    Returns None while no policy is active (empty shell). An allowlist entry is a host
    (`127.0.0.1`, `api.example.com`) or a URL prefix (`http://127.0.0.1:8001/`). Calling this
    check before every outgoing call of the tool server is the work of workshop 10d.
    """
    if not is_policy_enforced():
        return None
    host = (urlsplit(url).hostname or "").lower()
    for entry in policy()["allowlist"]:
        entry = str(entry).strip().lower()
        if "://" in entry:
            if url.lower().startswith(entry):
                return True
        elif host == entry:
            return True
    return False
