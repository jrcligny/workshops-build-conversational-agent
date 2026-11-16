
"""API HTTP de la recherche documentaire."""

from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from application.auth import decoder_jeton
from documentation.indexation import reconstruire
from documentation.recherche import etat_index, get_passage, rechercher
from socle.config import reglages

app = FastAPI(title="Recherche documentaire du fil rouge", version="0.1.0")

_JOURNAL: list[dict] = []


class RechercheIn(BaseModel):
    requete: str
    k: int = 5
    seuil: float = 0.05


class ReconstruireIn(BaseModel):
    inclure_retires: bool = False


def _identite(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="identité manquante")
    try:
        return decoder_jeton(authorization.split(" ", 1)[1].strip())
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="jeton invalide") from exc


@app.get("/sante")
def sante():
    return {"statut": "ok"}


@app.post("/recherche")
def api_recherche(corps: RechercheIn, authorization: str | None = Header(default=None)):
    identite = _identite(authorization)
    resultat = rechercher(corps.requete, identite["organisation"], identite["role"], k=corps.k, seuil=corps.seuil)
    _JOURNAL.append({"utilisateur": identite.get("sub"), "organisation": identite.get("organisation"), "requete": corps.requete})
    return resultat


@app.get("/passages/{passage_id}")
def api_passage(passage_id: str, authorization: str | None = Header(default=None)):
    _identite(authorization)
    passage = get_passage(passage_id)
    if not passage:
        raise HTTPException(status_code=404, detail="passage introuvable")
    return passage


@app.post("/indexation/reconstruire")
def api_reconstruire(corps: ReconstruireIn, authorization: str | None = Header(default=None)):
    # Réservé aux tests : jeton d'observation ou identité valide.
    auth = authorization or ""
    jeton = auth.split(" ", 1)[1].strip() if auth.lower().startswith("bearer ") else ""
    if jeton != reglages.jeton_observation:
        _identite(authorization)
    return reconstruire(inclure_retires=corps.inclure_retires)


@app.get("/indexation/etat")
def api_etat(authorization: str | None = Header(default=None)):
    _identite(authorization) if authorization else None
    return etat_index()


@app.get("/journal")
def api_journal(authorization: str | None = Header(default=None)):
    jeton = (authorization or "").split(" ", 1)[-1].strip()
    if jeton != reglages.jeton_observation:
        raise HTTPException(status_code=401, detail="jeton d'observation invalide")
    return list(_JOURNAL)


def vider_journal() -> None:
    _JOURNAL.clear()
