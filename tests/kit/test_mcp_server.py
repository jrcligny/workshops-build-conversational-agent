"""Le serveur MCP de la coquille démarre et n'expose aucun outil."""

from __future__ import annotations

import asyncio

import pytest
from mcp import Client

from socle.interface.chargeur import charger_serveur_mcp
from tests.communs.serveurs import attendre_port, lancer_uvicorn, port_libre

pytestmark = pytest.mark.socle


@pytest.fixture(scope="module")
def serveur_mcp_url():
    module = charger_serveur_mcp()
    port = port_libre()
    serveur = lancer_uvicorn(module.application(), port)
    attendre_port("127.0.0.1", port)
    yield f"http://127.0.0.1:{port}{module.CHEMIN_MCP}"
    serveur.should_exit = True


def test_serveur_mcp_demarre_et_liste_zero_outil(serveur_mcp_url):
    async def _verifier():
        async with Client(serveur_mcp_url) as client:
            assert client.server_info is not None
            assert client.server_info.name == "ateliers-outils"
            resultat = await client.list_tools()
            assert resultat.tools == []

    asyncio.run(_verifier())
