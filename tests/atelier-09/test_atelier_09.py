"""Tests de bout en bout de l'atelier 09. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


import asyncio

from mcp import Client

from socle.interface.chargeur import charger_serveur_mcp
from tests.communs.serveurs import attendre_port, lancer_uvicorn, port_libre

OUTILS_REMPLACES = {"rechercher_client", "lister_commandes", "lister_commandes_client", "rechercher_clients"}


@pytest.fixture(scope="module")
def serveur_mcp_url():
    module = charger_serveur_mcp()
    port = port_libre()
    serveur = lancer_uvicorn(module.application(), port)
    attendre_port("127.0.0.1", port)
    yield f"http://127.0.0.1:{port}{module.CHEMIN_MCP}"
    serveur.should_exit = True


def _catalogue(url: str) -> list:
    async def _liste():
        async with Client(url) as client:
            resultat = await client.list_tools()
            return list(resultat.tools)

    return asyncio.run(_liste())


def test_outils_servis_par_mcp(client_chat, observation):
    tour, trace = tour_reussi(client_chat, "Quel est le total des commandes de Martin Durand ?")
    assert "mcp" in plat(trace).lower() or trace.get("transport") == "mcp"
    journal = journal_metier(observation)
    assert journal, "l'application doit être appelée, via le serveur MCP, pas depuis un outil local silencieux"
    # plus d'appel HTTP direct depuis le harness : l'origine doit être le serveur d'outils
    assert any("mcp" in str(e).lower() or e.get("origine") == "mcp" or e.get("via") == "mcp" for e in journal) or "mcp" in plat(trace).lower()


def test_deux_clients_obtiennent_le_meme_catalogue(serveur_mcp_url):
    a = _catalogue(serveur_mcp_url)
    b = _catalogue(serveur_mcp_url)
    noms = [getattr(t, "name", None) or str(t) for t in a]
    assert noms, "le catalogue MCP de l'atelier 09 ne doit plus être vide"
    assert [getattr(t, "name", None) or str(t) for t in b] == noms
    assert not (OUTILS_REMPLACES & set(noms)), "les deux outils spécialisés du chapitre 5 doivent avoir disparu"


def test_filtre_mal_forme_erreur_exploitable(client_chat):
    tour, trace = tour_reussi(client_chat, "Interroge les commandes avec le filtre statut==LIVR (ce n'est pas un statut valide).")
    texte = (tour.texte + plat(outils(trace))).lower()
    assert "erreur" in texte or "invalide" in texte or "corriger" in texte or "statut" in texte
    assert "livr" in texte or "livree" in texte or "livrée" in texte or "libellé" in texte or "libelle" in texte or "valeurs" in texte


def test_question_comptable_via_interrogation_generique(client_chat, observation):
    from tests.communs.client_chat import ClientChat
    comptable = ClientChat(client_chat.base_url)
    comptable.ouvrir(utilisateur_id="nina-comptable", role="comptable", organisation="organisation-a")
    tour, trace = tour_reussi(comptable, "Quel est le total des factures en attente ?")
    assert outils(trace)
    plat_outils = plat(outils(trace)).lower()
    assert "interr" in plat_outils or "generique" in plat_outils or "générique" in plat_outils or "agreger" in plat_outils or "agrég" in plat_outils or "total" in plat_outils
