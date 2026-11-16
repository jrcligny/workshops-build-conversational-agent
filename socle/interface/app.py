"""Interface de chat minimale : flux typés, client utilisé par les tests."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from socle.harness_base.contrat import Evenement, HarnessNonImplemente, Message, UtilisateurEssai
from socle.interface.chargeur import charger_harness

app = FastAPI(title="Interface de chat des ateliers", version="0.1.0")

_conversations: dict[str, dict] = {}
_historiques: dict[str, list[Message]] = defaultdict(list)
_confirmations: dict[str, bool] = {}
_interruptions: set[str] = set()
_harness = None
_urls: dict[str, str] = {}


def configurer(urls: dict[str, str] | None = None) -> None:
    global _urls
    _urls = urls or {}


def harness():
    global _harness
    if _harness is None:
        _harness = charger_harness()
    return _harness


def reinitialiser_conversations() -> None:
    _conversations.clear()
    _historiques.clear()
    _confirmations.clear()
    _interruptions.clear()
    global _harness
    _harness = None


class ConversationIn(BaseModel):
    utilisateur_id: str = "camille-renard"
    role: str = "charge_clientele"
    organisation: str = "organisation-a"
    jeton_application: str | None = None
    limites: dict | None = None


class MessageIn(BaseModel):
    texte: str
    pieces_jointes: list[str] = []
    interrompre: bool = False


class ConfirmationIn(BaseModel):
    confirme: bool = True


@app.get("/sante")
def sante():
    return {"statut": "ok"}


@app.get("/pieces-jointes")
def lister_pieces_jointes():
    """Point d'entrée du contrat pour l'atelier 15. La zone est vide dans la coquille."""
    from services.pieces_jointes.registre import lister

    return {"pieces_jointes": lister()}


@app.post("/conversations")
def creer_conversation(corps: ConversationIn):
    identifiant = uuid.uuid4().hex
    _conversations[identifiant] = corps.model_dump()
    _historiques[identifiant] = []
    return {"id": identifiant, "utilisateur": corps.model_dump()}


@app.post("/conversations/{conversation_id}/confirmation")
def confirmer(conversation_id: str, corps: ConfirmationIn):
    """Geste de confirmation de l'utilisateur (atelier 10b)."""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="conversation inconnue")
    _confirmations[conversation_id] = bool(corps.confirme)
    return {"ok": True, "confirme": bool(corps.confirme)}


@app.post("/conversations/{conversation_id}/interruption")
def interrompre(conversation_id: str):
    """Demande d'interruption du tour en cours (atelier 06)."""
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="conversation inconnue")
    _interruptions.add(conversation_id)
    return {"ok": True}


@app.post("/conversations/{conversation_id}/messages")
def envoyer_message(conversation_id: str, corps: MessageIn):
    if conversation_id not in _conversations:
        raise HTTPException(status_code=404, detail="conversation inconnue")
    meta = _conversations[conversation_id]
    utilisateur = UtilisateurEssai(
        id=meta["utilisateur_id"],
        role=meta["role"],
        organisation=meta["organisation"],
        jeton_application=meta.get("jeton_application"),
    )
    historique = list(_historiques[conversation_id])
    interruption = conversation_id in _interruptions or corps.interrompre
    confirmation = _confirmations.get(conversation_id, False)
    limites = meta.get("limites")

    def flux():
        try:
            evenements = list(
                harness().tour(
                    conversation_id,
                    corps.texte,
                    utilisateur,
                    historique,
                    pieces_jointes=corps.pieces_jointes,
                    interruption_demandee=interruption,
                    confirmation=confirmation,
                    limites=limites,
                )
            )
        except HarnessNonImplemente as exc:
            ev = Evenement(type="erreur", data={"detail": str(exc)})
            yield _sse(ev)
            yield _sse(Evenement(type="fin", data={"ok": False, "detail": str(exc)}))
            return
        except NotImplementedError as exc:
            detail = str(exc) or "Harness non implémenté (coquille vide)."
            yield _sse(Evenement(type="erreur", data={"detail": detail}))
            yield _sse(Evenement(type="fin", data={"ok": False, "detail": detail}))
            return
        except Exception as exc:  # noqa: BLE001
            yield _sse(Evenement(type="erreur", data={"detail": f"{type(exc).__name__}: {exc}"}))
            yield _sse(Evenement(type="fin", data={"ok": False, "detail": str(exc)}))
            return
        texte = ""
        for ev in evenements:
            if ev.type == "texte":
                texte += ev.data.get("contenu", "")
            yield _sse(ev)
        if not any(ev.type == "fin" for ev in evenements):
            yield _sse(Evenement(type="fin", data={"ok": True, "texte": texte}))
        # L'historique n'est mis à jour par le socle que si le harness a produit une fin réussie.
        if texte:
            _historiques[conversation_id].append(Message(role="user", contenu=corps.texte))
            _historiques[conversation_id].append(Message(role="assistant", contenu=texte))

    return StreamingResponse(flux(), media_type="text/event-stream")


def _sse(ev: Evenement) -> str:
    return f"event: {ev.type}\ndata: {json.dumps(ev.data, ensure_ascii=False)}\n\n"
