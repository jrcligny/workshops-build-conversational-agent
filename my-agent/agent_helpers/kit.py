"""The kit pieces your harness needs, gathered in one place.

What it gives you:
- `model_client()`: a `ModelClient` wired to the model proxy (`PROXY_URL`, read at each call).
  `generate(messages, tools=None, model="default")` makes **one** call and returns the raw
  OpenAI-style answer; `generate_stream()` splits the text; `embeddings()` returns vectors.
  It does not run the agent loop, execute tools nor keep the history: that is your work
  (workshops 03, 04 and 06). `model="fallback"` targets the fallback model (workshop 18).
- `ModelUnavailable` and `model_unavailable(exc)`: tell an outage of the model (5xx, 429,
  timeout) from a bug of the caller (workshop 18).
- `write_trace(trace)` and `new_id()`: append one JSONL line to the trace file, without
  secrets. The writer does not compose the trace: see `agent_helpers.trace`.
- `Event`, `Message`, `TestUser`: the types of the harness contract.
- `sandbox_policy()` and `is_egress_allowed(url)` (workshop 10d): read
  `my-agent/sandbox/policy.yaml` and evaluate a destination against its allowlist. They do
  not apply anything: checking every outgoing call is the work of workshop 10d.
- `skills_manifest()` and `skill_folders()` (workshop 14): read `my-agent/skills/`. Choosing,
  loading and offering the skills stays yours.
- `list_attachments()` (workshop 15): the files of `my-agent/attachments/`. Reading them
  without obeying them stays yours.
"""

from __future__ import annotations

import os
from pathlib import Path

from workshop_kit.services.attachments import registry as _attachments
from workshop_kit.services.sandbox import interface as _sandbox
from workshop_kit.services.skills_catalog import catalog as _skills
from workshop_kit.shell import tracer as _tracer
from workshop_kit.shell.harness_contract import Event, Message, TestUser
from workshop_kit.shell.model_client import ModelClient, ModelUnavailable, model_unavailable

DEFAULT_PROXY_URL = "http://127.0.0.1:8003"

__all__ = [
    "Event",
    "Message",
    "ModelClient",
    "ModelUnavailable",
    "TestUser",
    "is_egress_allowed",
    "list_attachments",
    "model_client",
    "model_unavailable",
    "new_id",
    "sandbox_policy",
    "skill_folders",
    "skills_manifest",
    "write_trace",
]


def model_client(timeout: float = 30.0) -> ModelClient:
    """A client of the model proxy; the URL is read from `PROXY_URL` at each call."""
    return ModelClient(os.environ.get("PROXY_URL", DEFAULT_PROXY_URL), timeout=timeout)


def write_trace(trace: dict) -> Path:
    return _tracer.write(trace)


def new_id() -> str:
    return _tracer.new_id()


def sandbox_policy() -> dict:
    """`{"active", "allowlist", "limits", "location"}` read from the sandbox policy file."""
    return _sandbox.policy()


def is_egress_allowed(url: str) -> bool | None:
    """True or False against the allowlist; None while the policy is inactive."""
    return _sandbox.is_egress_allowed(url)


def skills_manifest() -> dict:
    return _skills.load_manifest()


def skill_folders() -> list[Path]:
    return _skills.skill_folders()


def list_attachments() -> list[dict]:
    """`[{"id", "name", "path"}]` for each attached document."""
    return _attachments.list_attachments()
