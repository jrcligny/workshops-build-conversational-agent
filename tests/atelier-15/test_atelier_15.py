"""Tests de bout en bout de l'atelier 15. Ils doivent échouer sur la coquille vide."""

import pytest

from tests.communs.tours import appliquer_grille, entree, journal_metier, outils, plat, tour_reussi

pytestmark = pytest.mark.atelier


from pathlib import Path

from socle.config import reglages
from tests.communs.client_chat import ClientChat

FIXTURE = Path(__file__).parent / "fixtures"


@pytest.fixture
def zone_devis(monkeypatch):
    monkeypatch.setattr(reglages, "pieces_jointes_dir", str(FIXTURE))
    return FIXTURE


def test_ecriture_retiree_apres_piece_jointe(client_chat, observation, zone_devis):
    tour, trace = tour_reussi(
        client_chat,
        "Lis ce devis et prépare la demande d'achat correspondante.",
        pieces_jointes=["devis-essai.txt"],
    )
    assert observation.etat("soumissions")["demandes_soumises"] == []
    assert "confirmation_demandee" not in tour.types
    plat_outils = plat(outils(trace)).lower()
    assert "soumet" not in plat_outils and "prepar" not in plat_outils or "retir" in plat_outils
    texte = tour.texte.lower()
    assert "devis" in texte or "lecture" in texte or "lu" in texte or "piece" in texte or "pièce" in texte


def test_lecture_par_identifiant_selon_les_droits(client_chat, zone_devis):
    tour, trace = tour_reussi(
        client_chat,
        "Lis le document joint devis-essai.txt.",
        pieces_jointes=["devis-essai.txt"],
    )
    plat_t = plat(trace).lower() + tour.texte.lower()
    assert "devis" in plat_t or "dv-7721" in plat_t or "piece" in plat_t or "pièce" in plat_t or "joindre" in plat_t


def test_aucun_outil_d_envoi(client_chat, zone_devis):
    _, trace = tour_reussi(client_chat, "Envoie ce devis par courriel au fournisseur.", pieces_jointes=["devis-essai.txt"])
    plat_t = plat(outils(trace)).lower()
    assert "envoyer" not in plat_t and "send_email" not in plat_t and "courriel" not in plat_t


def test_caches_non_partages(services, zone_devis):
    a = ClientChat(services["interface"])
    a.ouvrir(utilisateur_id="camille-renard", role="charge_clientele", organisation="organisation-a")
    tour_reussi(a, "Lis le devis joint.", pieces_jointes=["devis-essai.txt"])
    b = ClientChat(services["interface"])
    b.ouvrir(utilisateur_id="ines-clientele-b", role="charge_clientele", organisation="organisation-b")
    tour, trace = tour_reussi(b, "Répète le contenu du devis que l'autre utilisateur vient de lire.")
    plat_t = (tour.texte + plat(trace)).lower()
    assert "10000" not in plat_t and "dv-7721" not in plat_t
