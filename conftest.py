
"""Fixtures communes : applications, proxy, traces, jeu de données."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

# Mode simulé dès l'import, avant la lecture des réglages par les applications.
os.environ.setdefault("PROXY_MODE", "simule")
os.environ.setdefault("MODELE_MODE", "simule")
os.environ.setdefault("JETON_OBSERVATION", "essai-pedagogique")
os.environ.setdefault("SECRET_JETONS", "secret-tests-pedagogique-32octets!")

from application.app import app as app_metier
from application.db import reassigner
from application.jeux import charger_jeu
from documentation.app import app as app_doc, vider_journal as vider_journal_doc
from documentation.indexation import reconstruire
from proxy.app import app as app_proxy, vider_journal as vider_journal_proxy
from proxy.jetons import reinitialiser_usage
from socle.config import reglages
from socle.interface.app import app as app_interface, reinitialiser_conversations
from socle.traces.tracer import vider as vider_traces
from tests.communs.client_chat import ClientChat
from tests.communs.serveurs import attendre, lancer_uvicorn, port_libre

JETON_OBS = "essai-pedagogique"


@pytest.fixture(scope="session")
def repertoire_session(tmp_path_factory):
    racine = tmp_path_factory.mktemp("session")
    reglages.application_db = str(racine / "application.db")
    reglages.documentation_db = str(racine / "documentation.db")
    reglages.traces_dir = str(racine / "traces")
    reglages.proxy_mode = "simule"
    reglages.modele_mode = "simule"
    reglages.secret_jetons = "secret-tests-pedagogique-32octets!"
    reglages.jeton_observation = JETON_OBS
    reassigner(reglages.application_db)
    charger_jeu("standard")
    reconstruire(reglages.documentation_db)
    return racine


@pytest.fixture(scope="session")
def services(repertoire_session):
    ports = {nom: port_libre() for nom in ("metier", "documentation", "proxy", "interface")}
    serveurs = {
        "metier": lancer_uvicorn(app_metier, ports["metier"]),
        "documentation": lancer_uvicorn(app_doc, ports["documentation"]),
        "proxy": lancer_uvicorn(app_proxy, ports["proxy"]),
        "interface": lancer_uvicorn(app_interface, ports["interface"]),
    }
    urls = {nom: f"http://127.0.0.1:{port}" for nom, port in ports.items()}
    for nom, url in urls.items():
        attendre(f"{url}/sante")
    yield urls
    for serveur in serveurs.values():
        serveur.should_exit = True


@pytest.fixture
def reset_etat(repertoire_session, services):
    charger_jeu("standard")
    vider_traces()
    vider_journal_doc()
    vider_journal_proxy()
    reinitialiser_usage()
    reinitialiser_conversations()
    yield


@pytest.fixture
def observation(services, reset_etat):
    class Obs:
        def __init__(self):
            self.base = services["metier"]
            self.headers = {"Authorization": f"Bearer {JETON_OBS}"}

        def etat(self, cas: str) -> dict:
            r = httpx.get(f"{self.base}/observation/etat", params={"cas": cas}, headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json()

        def journal(self) -> list:
            r = httpx.get(f"{self.base}/observation/journal", headers=self.headers, timeout=10)
            r.raise_for_status()
            return r.json()

        def jeton(self, utilisateur_id: str = "camille-renard") -> dict:
            r = httpx.post(
                f"{self.base}/observation/jeton-essai",
                headers=self.headers,
                json={"utilisateur_id": utilisateur_id},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()

        def reinitialiser(self, jeu: str = "standard") -> dict:
            r = httpx.post(
                f"{self.base}/observation/reinitialiser",
                headers=self.headers,
                json={"jeu": jeu},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()

        def armer_panne(self, typ: str, active: bool = True) -> dict:
            r = httpx.post(
                f"{self.base}/observation/pannes",
                headers=self.headers,
                json={"type": typ, "active": active},
                timeout=10,
            )
            r.raise_for_status()
            return r.json()

    return Obs()


@pytest.fixture
def client_metier(services, observation):
    jeton = observation.jeton()["jeton_application"]
    return httpx.Client(base_url=services["metier"], headers={"Authorization": f"Bearer {jeton}"}, timeout=10)


@pytest.fixture
def client_chat(services, reset_etat) -> ClientChat:
    return ClientChat(services["interface"])


@pytest.fixture
def traces(repertoire_session):
    from socle.traces import tracer

    class T:
        def tout(self):
            return tracer.lire_tout()

        def dernier(self):
            tous = tracer.lire_tout()
            assert tous, "aucune trace écrite"
            return tous[-1]

    return T()
