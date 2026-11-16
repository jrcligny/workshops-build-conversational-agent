
import httpx
import pytest

from outils.atelier import ATELIERS, dossier_tests
from tests.communs.client_chat import ClientChat

pytestmark = pytest.mark.socle


def test_interface_sante(services):
    r = httpx.get(f"{services['interface']}/sante", timeout=5)
    assert r.status_code == 200


def test_coquille_renvoie_une_erreur_explicite(client_chat):
    tour = client_chat.tour("Où en est la commande CMD-1042 de Martin Durand ?")
    assert tour.ok is False
    assert tour.erreur
    assert "atelier 03" in tour.erreur.lower() or "system prompt" in tour.erreur.lower() or "boucle" in tour.erreur.lower()
    assert "fin" in tour.types


def test_tous_les_dossiers_d_ateliers_existent():
    manquants = [i for i in ATELIERS if not dossier_tests(i).is_dir()]
    assert manquants == []


def test_traces_vides_sur_la_coquille(client_chat, traces):
    client_chat.tour("bonjour")
    assert traces.tout() == []
