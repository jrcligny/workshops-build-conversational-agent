"""Sandbox policy of the tool server (workshop 07), degraded mode without a container.

The policy lives in sandbox/policy.yaml (read through the kit's `policy()`). Egress is filtered in the
HTTP client of the tool server: only http(s) destinations whose host is on the allowlist are reached,
and no tool reads or writes a file. This is less safe than a container with a read-only file system
and an egress proxy: a bug in the server itself would not be contained.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from agent_sdk.sandbox import is_egress_allowed, policy

DEFAULT_LIMITS = {"duration_s": 120, "token_budget": 60000}


def egress_decision(url: str) -> tuple[bool, str]:
    """The kit's allowlist check (host or URL prefix), restricted to http(s) destinations."""
    allowed = is_egress_allowed(url)
    if allowed is None:
        return True, "no sandbox policy active"
    scheme = urlsplit(url).scheme
    if scheme not in ("http", "https"):
        return False, f"scheme {scheme or '(none)'!r} refused: only http and https leave the sandbox"
    if allowed:
        return True, "destination on the sandbox allowlist"
    return False, f"destination {urlsplit(url).hostname or url!r} refused: not on the sandbox allowlist"


def turn_limits(requested: dict | None) -> dict:
    """Policy limits, tightened (never loosened) by the limits of the conversation."""
    limits = dict(DEFAULT_LIMITS)
    for key, value in (policy()["limits"] or {}).items():
        if value is not None:
            limits[key] = value
    for key, value in (requested or {}).items():
        if value is not None and key in limits:
            limits[key] = min(limits[key], value)
    return limits
