"""Location and interface of the sandbox, with no policy enforced.

In workshop 10d, the tool server will run in a container (unprivileged user,
read-only file system, egress proxy with an allowlist). This shell only exposes
the contract; the policy file itself lives in my-agent/sandbox/policy.yaml
(setting `sandbox_policy_file`). It enforces no policy.
"""

from __future__ import annotations

from pathlib import Path

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


def is_egress_allowed(_url: str) -> bool | None:
    """Returns None while no policy is active (empty shell)."""
    if not is_policy_enforced():
        return None
    # Implementing the allowlist is the work of workshop 10d.
    raise NotImplementedError("sandbox policy to implement (workshop 10d)")
