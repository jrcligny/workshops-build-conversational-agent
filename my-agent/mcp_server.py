"""Serveur MCP vide de la coquille.

Il démarre, répond au handshake du protocole MCP (SDK Python officiel `mcp`)
et n'expose aucun outil métier. Vous brancherez l'API métier à l'atelier 09.
Transport prévu : HTTP en flux (streamable-http), mode sans état.
"""

from __future__ import annotations

import os

from mcp.server import MCPServer

NOM = "ateliers-outils"
VERSION = "0.1.0"
CHEMIN_MCP = "/mcp"
HOTE_DEFAUT = "127.0.0.1"
PORT_DEFAUT = 8004


def creer_serveur() -> MCPServer:
    return MCPServer(
        name=NOM,
        version=VERSION,
        instructions=(
            "Coquille vide : aucun outil métier n'est encore exposé. "
            "À l'atelier 09, vous migrerez les outils vers ce serveur sans état "
            "et vous les brancherez sur l'API métier."
        ),
    )


def application():
    """Application Starlette servie par uvicorn (tests et lancement local)."""
    return creer_serveur().streamable_http_app(
        stateless_http=True,
        json_response=True,
        streamable_http_path=CHEMIN_MCP,
        host=HOTE_DEFAUT,
    )


if __name__ == "__main__":
    port = int(os.environ.get("MCP_PORT", str(PORT_DEFAUT)))
    hote = os.environ.get("MCP_HOST", HOTE_DEFAUT)
    creer_serveur().run(
        transport="streamable-http",
        host=hote,
        port=port,
        stateless_http=True,
        json_response=True,
        streamable_http_path=CHEMIN_MCP,
    )
