
"""Jetons de cours, distincts de la clé Azure, et quotas par étudiant."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Header, HTTPException

from socle.config import reglages

# Jetons d'essai livrés avec le dépôt (pas la clé Azure).
ETUDIANTS = {
    "etudiant-essai": {"nom": "Étudiant d'essai", "quota_jetons": None, "quota_requetes": None},
    "juge-essai": {"nom": "Juge d'essai", "quota_jetons": None, "quota_requetes": None},
}

# Compteurs en mémoire (suffisant en conception).
_usage: dict[str, dict[str, int]] = {}


def _cle_jour() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def emettre_jeton_etudiant(etudiant_id: str) -> str:
    if etudiant_id not in ETUDIANTS:
        ETUDIANTS[etudiant_id] = {"nom": etudiant_id, "quota_jetons": None, "quota_requetes": None}
    payload = {
        "sub": etudiant_id,
        "typ": "cours",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(days=30)).timestamp()),
    }
    return jwt.encode(payload, reglages.secret_jetons, algorithm="HS256")


def exiger_etudiant(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="jeton de cours manquant")
    jeton = authorization.split(" ", 1)[1].strip()
    # Les jetons prédéfinis « etudiant-essai » / « juge-essai » sont acceptés tels quels en simulé.
    if jeton in ETUDIANTS:
        return {"sub": jeton, "typ": "cours"}
    try:
        claims = jwt.decode(jeton, reglages.secret_jetons, algorithms=["HS256"])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="jeton de cours invalide") from exc
    if claims.get("typ") != "cours":
        raise HTTPException(status_code=401, detail="jeton de cours invalide")
    return claims


def consommer(etudiant_id: str, tokens: int) -> None:
    jour = _cle_jour()
    usage = _usage.setdefault(etudiant_id, {"jour": jour, "tokens": 0, "requetes": 0})
    if usage["jour"] != jour:
        usage.update({"jour": jour, "tokens": 0, "requetes": 0})
    fiche = ETUDIANTS.get(etudiant_id, {})
    q_tok = fiche.get("quota_jetons") or reglages.quota_jetons_par_jour
    q_req = fiche.get("quota_requetes") or reglages.quota_requetes_par_jour
    if usage["requetes"] + 1 > q_req or usage["tokens"] + tokens > q_tok:
        raise HTTPException(status_code=429, detail="quota étudiant dépassé")
    usage["requetes"] += 1
    usage["tokens"] += tokens


def usage(etudiant_id: str) -> dict[str, int]:
    return dict(_usage.get(etudiant_id, {"tokens": 0, "requetes": 0}))


def reinitialiser_usage() -> None:
    _usage.clear()
