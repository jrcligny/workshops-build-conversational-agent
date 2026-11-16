
"""Jetons d'identité : un jeton « application » au nom d'un utilisateur."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, Header, HTTPException

from socle.config import reglages

ALGORITHME = "HS256"
ROLES = {
    "charge_clientele",
    "acheteur",
    "comptable",
    "controleur_gestion",
    "sans_ecriture",
}


def emettre_jeton(
    utilisateur_id: str,
    role: str,
    organisation: str,
    typ: str = "application",
    duree_h: int = 12,
) -> str:
    maintenant = datetime.now(timezone.utc)
    payload = {
        "sub": utilisateur_id,
        "role": role,
        "organisation": organisation,
        "typ": typ,
        "iat": int(maintenant.timestamp()),
        "exp": int((maintenant + timedelta(hours=duree_h)).timestamp()),
    }
    return jwt.encode(payload, reglages.secret_jetons, algorithm=ALGORITHME)


def decoder_jeton(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, reglages.secret_jetons, algorithms=[ALGORITHME])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="jeton invalide") from exc


def utilisateur_depuis_entete(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="identité manquante")
    claims = decoder_jeton(authorization.split(" ", 1)[1].strip())
    if claims.get("typ") != "application":
        raise HTTPException(
            status_code=401,
            detail="l'API n'accepte qu'un jeton émis pour l'application au nom de l'utilisateur",
        )
    if claims.get("role") not in ROLES:
        raise HTTPException(status_code=401, detail="rôle inconnu")
    return claims


Identite = dict[str, Any]
exiger_identite = Depends(utilisateur_depuis_entete)
