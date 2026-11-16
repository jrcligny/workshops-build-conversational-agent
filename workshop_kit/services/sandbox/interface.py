"""Location and interface of the sandbox, with no policy enforced.

In workshop 10d, the tool server will run in a container (unprivileged user,
read-only file system, egress proxy with an allowlist). This shell only exposes
the contract and the location of the files; it enforces no policy.
"""

from __future__ import annotations

from pathlib import Path

import yaml

FOLDER = Path(__file__).resolve().parent
POLICY_FILE = FOLDER / "policy.yaml"


def policy() -> dict:
    data = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8")) or {}
    return {
        "active": bool(data.get("active")),
        "allowlist": list(data.get("allowlist") or []),
        "limits": dict(data.get("limits") or {}),
        "location": str(POLICY_FILE),
    }


def is_policy_enforced() -> bool:
    return policy()["active"]


def is_egress_allowed(_url: str) -> bool | None:
    """Returns None while no policy is active (empty shell)."""
    if not is_policy_enforced():
        return None
    # Implementing the allowlist is the work of workshop 10d.
    raise NotImplementedError("sandbox policy to implement (workshop 10d)")
