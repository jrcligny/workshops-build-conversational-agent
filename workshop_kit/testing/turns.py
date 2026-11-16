"""Aides partagées par les tests d'atelier. Tous exigent un tour réussi (rouge sur la coquille)."""

from __future__ import annotations

from socle.evaluation.juge import juger
from socle.traces.tracer import lire_tout


def tour_reussi(client_chat, message: str, **kwargs):
    tour = client_chat.tour(message, **kwargs)
    assert tour.ok, (
        f"le tour doit aboutir (texte + fin) ; reçu : ok={tour.ok}, erreur={tour.erreur!r}"
    )
    assert "texte" in tour.types
    assert "fin" in tour.types
    traces = lire_tout()
    assert traces, "une trace de tour est exigée"
    return tour, traces[-1]


def journal_metier(observation) -> list:
    return [e for e in observation.journal() if not str(e.get("route", "")).startswith("/observation")]


def entree(trace: dict) -> dict:
    return trace.get("entree") or {}


def outils(trace: dict) -> list:
    return list(trace.get("outils") or [])


def historique(trace: dict) -> list:
    return list(entree(trace).get("historique") or [])


def textes_role(trace: dict, role: str) -> list[str]:
    morceaux = []
    for m in historique(trace):
        r = (m.get("role") or "").lower()
        if r == role or r == ("assistant" if role == "assistant" else r):
            morceaux.append(m.get("contenu") or m.get("content") or "")
    return morceaux


def plat(obj) -> str:
    return str(obj)


def appliquer_grille(grille: dict, tour, trace=None) -> dict:
    verdict = juger(grille, {"reponse": tour.texte, "trace": plat(trace) if trace is not None else ""})
    assert verdict["reussi"], f"grille {grille.get('id')}: {verdict.get('justification')}"
    return verdict
