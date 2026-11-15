
"""Proxy compatible OpenAI : modes simulé et rejoué ; mode réel plus tard (Azure, clé côté serveur)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from proxy import rejeu, simule
from proxy.jetons import ETUDIANTS, emettre_jeton_etudiant, exiger_etudiant, consommer, usage
from socle.config import reglages

logger = logging.getLogger("proxy")

app = FastAPI(title="Proxy de modèles", version="0.1.0")
_JOURNAL: list[dict] = []
_SCRIPTS: list[dict] = []
_PANNES: dict[str, bool] = {}


class ChatIn(BaseModel):
    model: str | None = None
    messages: list[dict[str, Any]]
    stream: bool = False
    tools: list[dict[str, Any]] | None = None
    temperature: float | None = None


class EmbeddingsIn(BaseModel):
    model: str | None = None
    input: str | list[str]


class ScriptsIn(BaseModel):
    scripts: list[dict[str, Any]] = Field(default_factory=list)


def _mode() -> str:
    return (reglages.proxy_mode or "simule").lower()


def _journaliser(etudiant: str, route: str, modele: str, tokens: int, code: int) -> None:
    entree = {
        "etudiant": etudiant,
        "route": route,
        "modele": modele,
        "tokens": tokens,
        "code": code,
        "mode": _mode(),
    }
    _JOURNAL.append(entree)
    # Jamais de clé Azure dans les journaux.
    logger.info("appel proxy etudiant=%s route=%s tokens=%s code=%s", etudiant, route, tokens, code)


@app.get("/sante")
def sante():
    return {"statut": "ok", "mode": _mode(), "azure_cle_presente": bool(reglages.azure_openai_api_key)}


@app.post("/v1/chat/completions")
def chat(corps: ChatIn, etudiant: dict = Depends(exiger_etudiant)):
    if corps.stream:
        # En conception, le flux est simulé par une unique réponse ; l'interface découpe au besoin.
        pass
    if _PANNES.get("modele_principal"):
        modele = corps.model or ""
        # Le modèle de repli, s'il est demandé explicitement, reste joignable.
        if "repli" not in modele.lower() and "fallback" not in modele.lower():
            _journaliser(etudiant["sub"], "/v1/chat/completions", modele, 0, 503)
            raise HTTPException(status_code=503, detail="modèle principal indisponible")
    if _mode() == "reel":
        if not reglages.azure_openai_api_key:
            raise HTTPException(status_code=503, detail="mode réel indisponible : aucune clé Azure n'est configurée")
        raise HTTPException(status_code=503, detail="mode réel non activé pendant la conception")
    reponse = None
    if _mode() == "rejoue":
        reponse = rejeu.trouver(corps.messages)
    if reponse is None:
        reponse = simule.completer(corps.messages, _SCRIPTS)
    tokens = int((reponse.get("usage") or {}).get("total_tokens") or 16)
    try:
        consommer(etudiant["sub"], tokens)
    except HTTPException as exc:
        _journaliser(etudiant["sub"], "/v1/chat/completions", reponse.get("model", ""), tokens, exc.status_code)
        raise
    _journaliser(etudiant["sub"], "/v1/chat/completions", reponse.get("model", ""), tokens, 200)
    return reponse


@app.post("/v1/embeddings")
def embeddings(corps: EmbeddingsIn, etudiant: dict = Depends(exiger_etudiant)):
    if _mode() == "reel":
        if not reglages.azure_openai_api_key:
            raise HTTPException(status_code=503, detail="mode réel indisponible : aucune clé Azure n'est configurée")
        raise HTTPException(status_code=503, detail="mode réel non activé pendant la conception")
    textes = corps.input if isinstance(corps.input, list) else [corps.input]
    reponse = simule.embeddings(textes)
    tokens = int((reponse.get("usage") or {}).get("total_tokens") or len(textes))
    consommer(etudiant["sub"], tokens)
    _journaliser(etudiant["sub"], "/v1/embeddings", reponse.get("model", ""), tokens, 200)
    return reponse


@app.get("/journal")
def journal(etudiant: dict = Depends(exiger_etudiant)):
    # En conception, un étudiant d'essai peut lire le journal de test.
    return list(_JOURNAL)


@app.post("/_test/scripts")
def charger_scripts(corps: ScriptsIn, etudiant: dict = Depends(exiger_etudiant)):
    _SCRIPTS.clear()
    _SCRIPTS.extend(corps.scripts)
    return {"n": len(_SCRIPTS)}


@app.post("/_test/jeton")
def jeton_essai(etudiant_id: str = "etudiant-essai"):
    """Émet un jeton de cours. Aucune clé Azure n'est renvoyée."""
    return {"etudiant_id": etudiant_id, "jeton": emettre_jeton_etudiant(etudiant_id), "predefinis": list(ETUDIANTS)}


@app.get("/_test/usage/{etudiant_id}")
def api_usage(etudiant_id: str):
    return usage(etudiant_id)


class PanneProxyIn(BaseModel):
    type: str
    active: bool = True


@app.post("/_test/pannes")
def armer_panne_proxy(corps: PanneProxyIn):
    """Arme une panne de test (modèle principal indisponible, atelier 18)."""
    _PANNES[corps.type] = corps.active
    return {"type": corps.type, "active": corps.active}


def vider_journal() -> None:
    _JOURNAL.clear()
    _SCRIPTS.clear()
    _PANNES.clear()
