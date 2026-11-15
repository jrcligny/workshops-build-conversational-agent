"""Démarrage des processus de test sur des ports locaux.

Fonctionne sous Windows et sous Unix : pas de fork, pas de signaux POSIX.
Les serveurs uvicorn tournent dans des fils d'exécution et s'arrêtent via
`should_exit`, pas via SIGTERM.
"""

from __future__ import annotations

import socket
import threading
import time

import httpx
import uvicorn


def port_libre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def attendre_port(hote: str, port: int, timeout: float = 8.0) -> None:
    """Attend que le port TCP accepte une connexion (sans HTTP GET)."""
    fin = time.time() + timeout
    dernier = None
    while time.time() < fin:
        with socket.socket() as s:
            s.settimeout(0.2)
            try:
                if s.connect_ex((hote, port)) == 0:
                    return
            except Exception as exc:  # noqa: BLE001
                dernier = exc
        time.sleep(0.05)
    raise RuntimeError(f"port injoignable : {hote}:{port} ({dernier})")


def attendre(url: str, timeout: float = 8.0) -> None:
    fin = time.time() + timeout
    dernier = None
    while time.time() < fin:
        try:
            r = httpx.get(url, timeout=0.5)
            if r.status_code < 500:
                return
        except Exception as exc:  # noqa: BLE001
            dernier = exc
        time.sleep(0.05)
    raise RuntimeError(f"service injoignable : {url} ({dernier})")


def lancer_uvicorn(app, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server
