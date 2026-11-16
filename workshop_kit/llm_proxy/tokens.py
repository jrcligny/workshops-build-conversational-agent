"""Course tokens, distinct from the Azure key, and per-student quotas."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Header, HTTPException

from workshop_kit.shell.config import settings

# Test tokens shipped with the repository (not the Azure key).
STUDENTS = {
    "test-student": {"name": "Test student", "token_quota": None, "request_quota": None},
    "test-judge": {"name": "Test judge", "token_quota": None, "request_quota": None},
}

# In-memory counters (enough during design).
_usage: dict[str, dict[str, Any]] = {}


def _day_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def issue_student_token(student_id: str) -> str:
    if student_id not in STUDENTS:
        STUDENTS[student_id] = {"name": student_id, "token_quota": None, "request_quota": None}
    payload = {
        "sub": student_id,
        "typ": "course",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
    }
    return jwt.encode(payload, settings.token_secret, algorithm="HS256")


def require_student(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing course token")
    token = authorization.split(" ", 1)[1].strip()
    # The predefined tokens "test-student" / "test-judge" are accepted as is in simulated mode.
    if token in STUDENTS:
        return {"sub": token, "typ": "course"}
    try:
        claims = jwt.decode(token, settings.token_secret, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid course token") from exc
    if claims.get("typ") != "course":
        raise HTTPException(status_code=401, detail="invalid course token")
    return claims


def consume(student_id: str, tokens: int) -> None:
    day = _day_key()
    counters = _usage.setdefault(student_id, {"day": day, "tokens": 0, "requests": 0})
    if counters["day"] != day:
        counters.update({"day": day, "tokens": 0, "requests": 0})
    record = STUDENTS.get(student_id, {})
    token_quota = record.get("token_quota") or settings.daily_token_quota
    request_quota = record.get("request_quota") or settings.daily_request_quota
    if counters["requests"] + 1 > request_quota or counters["tokens"] + tokens > token_quota:
        raise HTTPException(status_code=429, detail="student quota exceeded")
    counters["requests"] += 1
    counters["tokens"] += tokens


def usage(student_id: str) -> dict[str, Any]:
    return dict(_usage.get(student_id, {"tokens": 0, "requests": 0}))


def reset_usage() -> None:
    _usage.clear()
