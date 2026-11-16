"""Document search test app: SQLite FTS5 + sqlite-vec (vec0) hybrid index over the .txt corpus."""

import httpx
import pytest

from workshop_kit.apps.docs_search.indexing import connect, rebuild
from workshop_kit.apps.docs_search.search import index_state

pytestmark = pytest.mark.docs_search


def _search(services, token: str, body: dict) -> httpx.Response:
    return httpx.post(
        f"{services['docs_search']}/search",
        headers={"Authorization": f"Bearer {token}"},
        json=body,
        timeout=10,
    )


def test_index_rebuilt(session_dir):
    ids = {d["document_id"] for d in index_state()["documents"]}
    assert "proc-incomplete-deliveries" in ids
    assert "proc-incomplete-deliveries-v1" not in ids  # retired version absent by default


def test_incomplete_delivery_search_with_source(observation, services):
    token = observation.token("camille-renard")["app_token"]
    r = _search(services, token, {"query": "Que dit la procédure quand une livraison arrive incomplète ?", "k": 5})
    assert r.status_code == 200
    data = r.json()
    assert data["no_passage"] is False
    assert data["passages"]
    first = data["passages"][0]
    assert first["title"]
    assert first["section"]
    assert first["version"] == "2.1"
    assert first["address"]
    assert "incomplète" in first["text"].lower() or "incomplètes" in first["title"].lower()


def test_organization_filtering(observation, services):
    token_a = observation.token("camille-renard")["app_token"]
    r = _search(services, token_a, {"query": "Ateliers du Midi relance fournisseur trois jours", "k": 8, "threshold": 0.0})
    assert r.status_code == 200
    organizations = {p["organization"] for p in r.json()["passages"]}
    assert "organization-b" not in organizations


def test_accountant_audience_filtering(observation, services):
    token = observation.token("camille-renard")["app_token"]
    r = _search(services, token, {"query": "statuts de facture paid pending", "k": 8, "threshold": 0.0})
    assert r.status_code == 200
    audiences = {p["audience"] for p in r.json()["passages"]}
    assert "accountant" not in audiences


def test_empty_result_declared(observation, services):
    token = observation.token("camille-renard")["app_token"]
    r = _search(services, token, {"query": "xyzzy-made-up-term-without-any-document-42", "k": 5, "threshold": 0.9})
    assert r.status_code == 200
    data = r.json()
    assert data["no_passage"] is True
    assert data["passages"] == []


def test_reindexing_removes_old_version(session_dir):
    rebuild(include_retired=True)
    ids = {d["document_id"] for d in index_state()["documents"]}
    assert "proc-incomplete-deliveries-v1" in ids
    rebuild(include_retired=False)
    ids = {d["document_id"] for d in index_state()["documents"]}
    assert "proc-incomplete-deliveries-v1" not in ids


def test_lexical_branch_status_code(observation, services):
    token = observation.token("nina-accountant")["app_token"]
    r = _search(services, token, {"query": "statut paid", "k": 5, "threshold": 0.0})
    assert r.status_code == 200
    texts = " ".join(p["text"] + p["title"] for p in r.json()["passages"]).lower()
    assert "paid" in texts


def test_vec_version(session_dir):
    conn = connect()
    try:
        version = conn.execute("select vec_version()").fetchone()[0]
        assert version
        assert str(version).lower().startswith("v") or str(version)[0].isdigit()
    finally:
        conn.close()


def test_index_uses_a_vec0_table(session_dir):
    conn = connect()
    try:
        row = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'passages_vec'").fetchone()
        assert row is not None
        assert "vec0" in row[0]
        assert "distance_metric=cosine" in row[0] or "float[" in row[0]
    finally:
        conn.close()
