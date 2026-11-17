"""HTTP API of the document search application."""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from business_api.auth import decode_token
from docs_search.indexing import rebuild
from docs_search.search import get_passage, index_state, search
from workshop_config import settings

app = FastAPI(title="Document search of the running example", version="0.1.0")

_LOG: list[dict] = []


class SearchIn(BaseModel):
    query: str
    k: int = 5
    threshold: float = 0.3


class RebuildIn(BaseModel):
    include_retired: bool = False


def _identity(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing identity")
    try:
        return decode_token(authorization.split(" ", 1)[1].strip())
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="invalid token") from exc


def _bearer(authorization: str | None) -> str:
    auth = authorization or ""
    return auth.split(" ", 1)[1].strip() if auth.lower().startswith("bearer ") else ""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/search")
def api_search(body: SearchIn, authorization: str | None = Header(default=None)):
    identity = _identity(authorization)
    result = search(body.query, identity["organization"], identity["role"], k=body.k, threshold=body.threshold)
    _LOG.append({"user": identity.get("sub"), "organization": identity.get("organization"), "query": body.query})
    return result


@app.get("/passages/{passage_id}")
def api_passage(passage_id: str, authorization: str | None = Header(default=None)):
    _identity(authorization)
    passage = get_passage(passage_id)
    if not passage:
        raise HTTPException(status_code=404, detail="passage not found")
    return passage


@app.post("/indexing/rebuild")
def api_rebuild(body: RebuildIn, authorization: str | None = Header(default=None)):
    # Reserved for tests: observation token or a valid identity.
    if _bearer(authorization) != settings.observation_token:
        _identity(authorization)
    return rebuild(include_retired=body.include_retired)


@app.get("/indexing/state")
def api_index_state(authorization: str | None = Header(default=None)):
    # The observation token sees the whole index (tests); a user sees only what they may search.
    if _bearer(authorization) == settings.observation_token:
        return index_state()
    identity = _identity(authorization)
    return index_state(organization=identity["organization"], role=identity["role"])


@app.get("/log")
def api_log(authorization: str | None = Header(default=None)):
    if _bearer(authorization) != settings.observation_token:
        raise HTTPException(status_code=401, detail="invalid observation token")
    return list(_LOG)


def clear_log() -> None:
    _LOG.clear()
