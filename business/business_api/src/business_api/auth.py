"""Identity tokens: an "application" token issued on behalf of a user."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException

from workshop_config import settings

ALGORITHM = "HS256"
ROLES = {
    "customer_service",
    "buyer",
    "accountant",
    "financial_controller",
    "read_only",
}
# French display labels of the roles (the agent converses in French; codes stay English).
ROLE_LABELS = {
    "customer_service": "chargé de clientèle",
    "buyer": "acheteur",
    "accountant": "comptable",
    "financial_controller": "contrôleur de gestion",
    "read_only": "lecture seule",
}


def issue_token(
    user_id: str,
    role: str,
    organization: str,
    typ: str = "application",
    duration_h: int = 12,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "organization": organization,
        "typ": typ,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=duration_h)).timestamp()),
    }
    return jwt.encode(payload, settings.token_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.token_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid token") from exc


def user_from_header(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing identity")
    claims = decode_token(authorization.split(" ", 1)[1].strip())
    if claims.get("typ") != "application":
        raise HTTPException(
            status_code=401,
            detail="the API only accepts a token issued for the application on behalf of the user",
        )
    if claims.get("role") not in ROLES:
        raise HTTPException(status_code=401, detail="unknown role")
    return claims


Identity = dict[str, Any]
require_identity = Depends(user_from_header)
