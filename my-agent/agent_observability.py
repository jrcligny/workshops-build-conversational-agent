"""Trace masking: every turn is traced end to end, but no secret nor credential ever reaches the file."""

from __future__ import annotations

import re
from typing import Any

MASK = "[masqué]"

# Keys whose value is a credential, whatever it looks like (usage counters like "input_tokens" stay).
_SECRET_KEYS = re.compile(
    r"^(authorization|api[_-]?key|.*_api_key|password|passwd|secret|client_secret|cookie|set-cookie|"
    r"token|app_token|user_token|access_token|refresh_token|id_token|bearer|iban)$",
    re.IGNORECASE,
)
_SECRET_VALUES = [
    (re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]+"), MASK),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]*"), MASK),  # JWT
    (re.compile(r"(?i)\b(?:sk|pk|rk)-[A-Za-z0-9]{16,}"), MASK),  # API-key shaped
    (re.compile(r"(?i)\bauthorization\s*[:=]\s*\S+"), MASK),
    (re.compile(r"(?i)\b(?:api[_-]?key|password|secret)\s*[:=]\s*\S+"), MASK),
    (re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}\b"), MASK),  # IBAN
]
# Words that must not appear in a trace even as a label (header names, environment variable names).
_SECRET_WORDS = re.compile(r"(?i)authorization|azure_openai_api_key|bearer ")


def mask_text(text: str) -> str:
    for pattern, replacement in _SECRET_VALUES:
        text = pattern.sub(replacement, text)
    return _SECRET_WORDS.sub(MASK, text)


def mask(value: Any) -> Any:
    """Returns a masked copy of a trace (dicts, lists, strings), leaving the original untouched."""
    if isinstance(value, dict):
        return {
            k: (MASK if isinstance(k, str) and _SECRET_KEYS.match(k) and v not in (None, "") else mask(v))
            for k, v in value.items()
            if not (isinstance(k, str) and _SECRET_WORDS.search(k))
        }
    if isinstance(value, (list, tuple)):
        return [mask(v) for v in value]
    if isinstance(value, str):
        return mask_text(value)
    return value
