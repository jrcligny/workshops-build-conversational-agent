
import pytest

pytestmark = pytest.mark.application


def test_sante(services):
    import httpx
    r = httpx.get(f"{services['metier']}/sante", timeout=5)
    assert r.status_code == 200
    assert r.json()["statut"] == "ok"


def test_commande_typée(client_metier):
    r = client_metier.get("/commandes/CMD-1042")
    assert r.status_code == 200
    data = r.json()
    assert data["statut"] == "livree"
    assert data["reference"] == "CMD-1042"


def test_commande_inexistante(client_metier):
    r = client_metier.get("/commandes/CMD-1402")
    assert r.status_code == 404


def test_commande_supprimee_invisible_au_charge_de_clientele(client_metier):
    r = client_metier.get("/commandes/CMD-0881")
    assert r.status_code == 404


def test_homonymes(client_metier):
    r = client_metier.get("/clients", params={"nom": "Léa Martin"})
    assert r.status_code == 200
    noms = r.json()
    assert len(noms) == 2
    assert {c["id"] for c in noms} == {"C-MARTIN-LILLE", "C-MARTIN-LYON"}


def test_filtre_retard_horloge_figee(observation, client_metier):
    observation.reinitialiser("volume")
    r = client_metier.get("/clients/C-VOLUMEX/commandes", params={"filtre": "en_retard"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    assert all(c["en_retard"] for c in data["commandes"])
    # Reproductible grâce à la graine et à l'horloge figée.
    second = client_metier.get("/clients/C-VOLUMEX/commandes", params={"filtre": "en_retard"}).json()
    assert second["total"] == data["total"]


def test_cloisonnement_organisation(observation, services):
    import httpx
    jeton_b = observation.jeton("inès-clientele-b")["jeton_application"]
    r = httpx.get(
        f"{services['metier']}/commandes/CMD-1042",
        headers={"Authorization": f"Bearer {jeton_b}"},
        timeout=10,
    )
    assert r.status_code == 404


def test_sans_identite(services, reset_etat):
    import httpx
    r = httpx.get(f"{services['metier']}/commandes/CMD-1042", timeout=5)
    assert r.status_code == 401


def test_jeton_entree_refuse(observation, services):
    import httpx
    jeton = observation.jeton()["jeton_entree"]
    r = httpx.get(
        f"{services['metier']}/commandes/CMD-1042",
        headers={"Authorization": f"Bearer {jeton}"},
        timeout=10,
    )
    assert r.status_code == 401


def test_preparer_sans_effet_puis_soumettre(observation, services):
    import httpx
    jeton = observation.jeton("paul-acheteur")["jeton_application"]
    client = httpx.Client(base_url=services["metier"], headers={"Authorization": f"Bearer {jeton}"}, timeout=10)
    avant = observation.etat("soumissions")
    r = client.post("/demandes-achat/brouillons", json={"objet": "Ramettes", "montant": 120})
    assert r.status_code == 200
    brouillon_id = r.json()["id"]
    # Le brouillon n'a pas créé de demande soumise.
    assert len(observation.etat("soumissions")["demandes_soumises"]) == len(avant["demandes_soumises"])
    s = client.post(f"/brouillons/{brouillon_id}/soumettre")
    assert s.status_code == 200
    data = s.json()
    assert data["statut"] == "soumise"
    assert data["attribue_a"] == "agent"
    assert data["pour_le_compte_de"] == "paul-acheteur"
    assert observation.etat(data["demande_id"])["demande_achat"]["statut"] == "soumise"


def test_acheteur_seul_peut_preparer(observation, services):
    import httpx
    jeton = observation.jeton("camille-renard")["jeton_application"]
    r = httpx.post(
        f"{services['metier']}/demandes-achat/brouillons",
        headers={"Authorization": f"Bearer {jeton}"},
        json={"objet": "Interdit", "montant": 10},
        timeout=10,
    )
    assert r.status_code == 403


def test_soumission_issue_inconnue_une_seule_tentative(observation, services):
    import httpx
    jeton = observation.jeton("paul-acheteur")["jeton_application"]
    client = httpx.Client(base_url=services["metier"], headers={"Authorization": f"Bearer {jeton}"}, timeout=10)
    brouillon_id = client.post("/demandes-achat/brouillons", json={"objet": "Test panne", "montant": 15}).json()["id"]
    observation.armer_panne("issue_inconnue", True)
    r = client.post(f"/brouillons/{brouillon_id}/soumettre")
    assert r.status_code == 504
    # Aucune demande soumise.
    assert observation.etat(brouillon_id)["brouillon"]["soumis"] == 0
    observation.armer_panne("issue_inconnue", False)


def test_mediane_refusee(client_metier):
    r = client_metier.post("/sources/commandes/interroger", json={"agregat": "mediane"})
    assert r.status_code == 200
    data = r.json()
    assert data["refuse"] is True
    assert "total" in data["agregats_disponibles"]


def test_observation_catalogue(observation):
    cat = observation.reinitialiser("standard")
    assert "CMD-1042" in cat["cas"]
