
"""API HTTP de l'application métier (FastAPI + OpenAPI)."""

from __future__ import annotations

from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from application.auth import emettre_jeton, utilisateur_depuis_entete
from application.jeux import JEUX, catalogue_cas, charger_jeu, utilisateur as fiche_utilisateur
from application.services import (
    SOURCES,
    armer_panne,
    etat_cas,
    get_brouillon,
    get_client,
    get_commande,
    get_facture,
    get_reglages,
    interroger_source,
    journaliser,
    lire_journal,
    lister_commandes,
    panne_active,
    preparer_brouillon,
    rechercher_clients,
    resoudre_nom,
    set_reglages,
    soumettre_brouillon,
)
from socle.config import reglages

app = FastAPI(title="Application métier du fil rouge", version="0.1.0")

ROLES_ECRITURE = {
    "demande_achat": {"acheteur"},
    "approbation_facture": {"comptable"},
}


class ReinitialiserIn(BaseModel):
    jeu: str = "standard"


class JetonIn(BaseModel):
    utilisateur_id: str


class PanneIn(BaseModel):
    type: str | None = None
    active: bool = True


class InterrogerIn(BaseModel):
    filtres: dict[str, Any] = Field(default_factory=dict)
    limite: int | None = None
    agregat: str | None = None
    regroupement: str | None = None


class BrouillonDemandeIn(BaseModel):
    objet: str
    montant: float | None = None
    fournisseur_id: str | None = None


class BrouillonFactureIn(BaseModel):
    facture_id: str


class ReglagesIn(BaseModel):
    preferer_hors_taxes: bool


def _observation(authorization: str | None) -> None:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="jeton d'observation manquant")
    jeton = authorization.split(" ", 1)[1].strip()
    if jeton != reglages.jeton_observation:
        raise HTTPException(status_code=401, detail="jeton d'observation invalide")


@app.middleware("http")
async def journal_et_pannes(request: Request, call_next):
    identite = None
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        # On n'essaie pas de décoder ici le jeton d'observation.
        from application.auth import decoder_jeton
        try:
            identite = decoder_jeton(auth.split(" ", 1)[1].strip())
        except Exception:
            identite = None
    if request.url.path.startswith("/observation"):
        return await call_next(request)
    panne = panne_active()
    if panne == "indisponible" and request.method in {"GET", "POST"}:
        journaliser(request.method, request.url.path, identite, 503)
        return JSONResponse({"detail": "application indisponible"}, status_code=503)
    if panne == "latence":
        import time
        time.sleep(0.05)
    response = await call_next(request)
    journaliser(request.method, request.url.path, identite, response.status_code)
    return response


@app.get("/sante")
def sante():
    return {"statut": "ok"}


@app.get("/clients")
def api_clients(nom: str, identite: dict = Depends(utilisateur_depuis_entete)):
    return rechercher_clients(nom, identite)


@app.get("/clients/{client_id}")
def api_client(client_id: str, identite: dict = Depends(utilisateur_depuis_entete)):
    client = get_client(client_id, identite)
    if not client:
        raise HTTPException(status_code=404, detail="client introuvable")
    return client


@app.get("/clients/{client_id}/commandes")
def api_commandes_client(
    client_id: str,
    filtre: str | None = None,
    limite: int | None = None,
    identite: dict = Depends(utilisateur_depuis_entete),
):
    if not get_client(client_id, identite):
        raise HTTPException(status_code=404, detail="client introuvable")
    return lister_commandes(client_id, identite, filtre=filtre, limite=limite)


@app.get("/commandes/{reference}")
def api_commande(reference: str, identite: dict = Depends(utilisateur_depuis_entete)):
    commande = get_commande(reference, identite)
    if not commande:
        raise HTTPException(status_code=404, detail="commande introuvable")
    return commande


@app.get("/resolution")
def api_resolution(type: str, nom: str, identite: dict = Depends(utilisateur_depuis_entete)):
    return resoudre_nom(type, nom, identite)


@app.get("/sources")
def api_sources(identite: dict = Depends(utilisateur_depuis_entete)):
    return [{"nom": nom, "description": meta["description"]} for nom, meta in SOURCES.items()]


@app.get("/sources/{nom}")
def api_source(nom: str, identite: dict = Depends(utilisateur_depuis_entete)):
    if nom not in SOURCES:
        raise HTTPException(status_code=404, detail="source inconnue")
    return {"nom": nom, **SOURCES[nom]}


@app.post("/sources/{nom}/interroger")
def api_interroger(nom: str, corps: InterrogerIn, identite: dict = Depends(utilisateur_depuis_entete)):
    try:
        return interroger_source(nom, identite, corps.filtres, corps.limite, corps.agregat, corps.regroupement)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _exiger_role(identite: dict, typ: str) -> None:
    if identite.get("role") not in ROLES_ECRITURE[typ]:
        raise HTTPException(status_code=403, detail="droit d'écriture insuffisant")


@app.post("/demandes-achat/brouillons")
def api_preparer_demande(corps: BrouillonDemandeIn, identite: dict = Depends(utilisateur_depuis_entete)):
    _exiger_role(identite, "demande_achat")
    return preparer_brouillon("demande_achat", corps.model_dump(), identite)


@app.post("/factures/{facture_id}/approbation/brouillons")
def api_preparer_facture(facture_id: str, identite: dict = Depends(utilisateur_depuis_entete)):
    _exiger_role(identite, "approbation_facture")
    if not get_facture(facture_id, identite):
        raise HTTPException(status_code=404, detail="facture introuvable")
    return preparer_brouillon("approbation_facture", {"facture_id": facture_id}, identite)


@app.get("/brouillons/{brouillon_id}")
def api_brouillon(brouillon_id: str, identite: dict = Depends(utilisateur_depuis_entete)):
    brouillon = get_brouillon(brouillon_id, identite)
    if not brouillon:
        raise HTTPException(status_code=404, detail="brouillon introuvable")
    return brouillon


@app.post("/brouillons/{brouillon_id}/soumettre")
def api_soumettre(brouillon_id: str, identite: dict = Depends(utilisateur_depuis_entete)):
    brouillon = get_brouillon(brouillon_id, identite)
    if not brouillon:
        raise HTTPException(status_code=404, detail="brouillon introuvable")
    typ = brouillon["type"]
    _exiger_role(identite, typ)
    try:
        return soumettre_brouillon(brouillon_id, identite)
    except RuntimeError as exc:
        if str(exc) == "issue_inconnue":
            raise HTTPException(status_code=504, detail="issue inconnue") from exc
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/factures/{facture_id}")
def api_facture(facture_id: str, identite: dict = Depends(utilisateur_depuis_entete)):
    facture = get_facture(facture_id, identite)
    if not facture:
        raise HTTPException(status_code=404, detail="facture introuvable")
    return facture


@app.get("/reglages")
def api_get_reglages(identite: dict = Depends(utilisateur_depuis_entete)):
    return get_reglages(identite)


@app.post("/reglages")
def api_set_reglages(corps: ReglagesIn, identite: dict = Depends(utilisateur_depuis_entete)):
    return set_reglages(identite, corps.preferer_hors_taxes)


# --- Observation (jeton pédagogique, jamais un outil) ---


@app.post("/observation/reinitialiser")
def obs_reset(corps: ReinitialiserIn, request: Request):
    _observation(request.headers.get("authorization"))
    if corps.jeu not in JEUX:
        raise HTTPException(status_code=400, detail=f"jeu inconnu : {corps.jeu}")
    charger_jeu(corps.jeu)
    return {"jeu": corps.jeu, "cas": catalogue_cas()}


@app.get("/observation/etat")
def obs_etat(cas: str, request: Request):
    _observation(request.headers.get("authorization"))
    return etat_cas(cas)


@app.get("/observation/journal")
def obs_journal(request: Request):
    _observation(request.headers.get("authorization"))
    return lire_journal()


@app.post("/observation/pannes")
def obs_pannes(corps: PanneIn, request: Request):
    _observation(request.headers.get("authorization"))
    armer_panne(corps.type, corps.active)
    return {"type": corps.type, "active": corps.active}


@app.post("/observation/jeton-essai")
def obs_jeton(corps: JetonIn, request: Request):
    _observation(request.headers.get("authorization"))
    fiche = fiche_utilisateur(corps.utilisateur_id)
    if not fiche:
        raise HTTPException(status_code=404, detail="utilisateur d'essai inconnu")
    jeton = emettre_jeton(fiche["id"], fiche["role"], fiche["organisation_id"], typ="application")
    jeton_entree = emettre_jeton(fiche["id"], fiche["role"], fiche["organisation_id"], typ="entree")
    return {
        "utilisateur": fiche,
        "jeton_application": jeton,
        "jeton_entree": jeton_entree,
        "commentaire": "Le jeton d'entrée simule celui reçu par le serveur d'outils ; l'API métier n'accepte que le jeton application.",
    }


@app.get("/observation/catalogue")
def obs_catalogue(request: Request):
    _observation(request.headers.get("authorization"))
    return catalogue_cas()


def creer_application() -> FastAPI:
    return app
