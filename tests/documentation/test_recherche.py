
import pytest

pytestmark = pytest.mark.documentation


def test_index_reconstruit(repertoire_session):
    from documentation.recherche import etat_index
    etat = etat_index()
    ids = {d["document_id"] for d in etat["documents"]}
    assert "proc-livraisons-incompletes" in ids
    assert "proc-livraisons-incompletes-v1" not in ids  # version retirée absente par défaut


def test_recherche_livraison_incomplete_avec_source(observation, services):
    import httpx
    jeton = observation.jeton("camille-renard")["jeton_application"]
    r = httpx.post(
        f"{services['documentation']}/recherche",
        headers={"Authorization": f"Bearer {jeton}"},
        json={"requete": "Que prévoit la procédure si une livraison arrive incomplète ?", "k": 5},
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["aucun_passage"] is False
    assert data["passages"]
    premier = data["passages"][0]
    assert premier["titre"]
    assert premier["section"]
    assert premier["version"] == "2.1"
    assert premier["adresse"]
    assert "incomplète" in premier["texte"].lower() or "incompletes" in premier["titre"].lower()


def test_filtrage_organisation(observation, services):
    import httpx
    jeton_a = observation.jeton("camille-renard")["jeton_application"]
    r = httpx.post(
        f"{services['documentation']}/recherche",
        headers={"Authorization": f"Bearer {jeton_a}"},
        json={"requete": "Ateliers du Midi relance fournisseur trois jours", "k": 8, "seuil": 0.0},
        timeout=10,
    )
    assert r.status_code == 200
    orgs = {p["organisation"] for p in r.json()["passages"]}
    assert "organisation-b" not in orgs


def test_filtrage_public_comptable(observation, services):
    import httpx
    jeton = observation.jeton("camille-renard")["jeton_application"]
    r = httpx.post(
        f"{services['documentation']}/recherche",
        headers={"Authorization": f"Bearer {jeton}"},
        json={"requete": "statuts de facture reglee en_attente", "k": 8, "seuil": 0.0},
        timeout=10,
    )
    assert r.status_code == 200
    publics = {p["public_vise"] for p in r.json()["passages"]}
    assert "comptable" not in publics


def test_resultat_vide_declare(observation, services):
    import httpx
    jeton = observation.jeton("camille-renard")["jeton_application"]
    r = httpx.post(
        f"{services['documentation']}/recherche",
        headers={"Authorization": f"Bearer {jeton}"},
        json={"requete": "xyzzy-terme-invente-sans-document-associe-42", "k": 5, "seuil": 0.9},
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["aucun_passage"] is True
    assert data["passages"] == []


def test_reindexation_retire_ancienne_version(repertoire_session):
    from documentation.indexation import reconstruire
    from documentation.recherche import etat_index
    reconstruire(inclure_retires=True)
    ids = {d["document_id"] for d in etat_index()["documents"]}
    assert "proc-livraisons-incompletes-v1" in ids
    reconstruire(inclure_retires=False)
    ids = {d["document_id"] for d in etat_index()["documents"]}
    assert "proc-livraisons-incompletes-v1" not in ids


def test_branche_lexicale_code_statut(observation, services):
    import httpx
    jeton = observation.jeton("nina-comptable")["jeton_application"]
    r = httpx.post(
        f"{services['documentation']}/recherche",
        headers={"Authorization": f"Bearer {jeton}"},
        json={"requete": "statut reglee", "k": 5, "seuil": 0.0},
        timeout=10,
    )
    assert r.status_code == 200
    textes = " ".join(p["texte"] + p["titre"] for p in r.json()["passages"]).lower()
    assert "reglee" in textes or "réglée" in textes
