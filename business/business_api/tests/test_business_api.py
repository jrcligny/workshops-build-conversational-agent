"""Business API test app: orders, customers, drafts, roles, two organizations, observation endpoint."""

import httpx
import pytest

pytestmark = pytest.mark.business_api


def test_health(services):
    r = httpx.get(f"{services['business_api']}/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_typical_order(business_client):
    r = business_client.get("/orders/CMD-1042")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "delivered"
    assert data["reference"] == "CMD-1042"


def test_missing_order(business_client):
    r = business_client.get("/orders/CMD-1402")
    assert r.status_code == 404


def test_deleted_order_hidden_from_customer_service(business_client):
    r = business_client.get("/orders/CMD-0881")
    assert r.status_code == 404


def test_namesakes(business_client):
    r = business_client.get("/customers", params={"name": "Léa Martin"})
    assert r.status_code == 200
    customers = r.json()
    assert len(customers) == 2
    assert {c["id"] for c in customers} == {"C-MARTIN-LILLE", "C-MARTIN-LYON"}


def test_late_filter_with_frozen_clock(observation, business_client):
    observation.reset("volume")
    r = business_client.get("/customers/C-VOLUMEX/orders", params={"filter": "late"})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 0
    assert all(o["late"] for o in data["orders"])
    # Reproducible thanks to the fixed seed and the frozen clock.
    second = business_client.get("/customers/C-VOLUMEX/orders", params={"filter": "late"}).json()
    assert second["total"] == data["total"]


def test_retrieval_cap_and_offset(observation, business_client):
    observation.reset("volume")
    late = business_client.get("/customers/C-VOLUMEX/orders", params={"filter": "late", "limit": 20}).json()
    assert (late["total"], late["total_status"], late["truncated"], late["next_offset"]) == (60, "exact", True, 20)
    rest = business_client.get(
        "/customers/C-VOLUMEX/orders", params={"filter": "late", "limit": 20, "offset": 20}
    ).json()
    assert {o["reference"] for o in rest["orders"]}.isdisjoint(o["reference"] for o in late["orders"])
    every = business_client.get("/customers/C-VOLUMEX/orders").json()
    assert (every["total"], every["total_status"], every["next_offset"]) == (200, "minimum", None)


def test_organization_isolation(observation, services):
    token_b = observation.token("ines-service-b")["app_token"]
    r = httpx.get(
        f"{services['business_api']}/orders/CMD-1042",
        headers={"Authorization": f"Bearer {token_b}"},
        timeout=10,
    )
    assert r.status_code == 404


def test_no_identity(services, reset_state):
    r = httpx.get(f"{services['business_api']}/orders/CMD-1042", timeout=5)
    assert r.status_code == 401


def test_entry_token_refused(observation, services):
    token = observation.token()["entry_token"]
    r = httpx.get(
        f"{services['business_api']}/orders/CMD-1042",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    assert r.status_code == 401


def test_prepare_has_no_effect_then_submit(observation, services):
    token = observation.token("paul-buyer")["app_token"]
    client = httpx.Client(base_url=services["business_api"], headers={"Authorization": f"Bearer {token}"}, timeout=10)
    before = observation.state("submissions")
    r = client.post("/purchase-requests/drafts", json={"subject": "Paper reams", "amount": 120})
    assert r.status_code == 200
    draft_id = r.json()["id"]
    # The draft did not create a submitted request.
    assert len(observation.state("submissions")["submitted_requests"]) == len(before["submitted_requests"])
    s = client.post(f"/drafts/{draft_id}/submit")
    assert s.status_code == 200
    data = s.json()
    assert data["status"] == "submitted"
    assert data["assigned_to"] == "agent"
    assert data["on_behalf_of"] == "paul-buyer"
    assert observation.state(data["request_id"])["purchase_request"]["status"] == "submitted"


def test_only_buyer_can_prepare(observation, services):
    token = observation.token("camille-renard")["app_token"]
    r = httpx.post(
        f"{services['business_api']}/purchase-requests/drafts",
        headers={"Authorization": f"Bearer {token}"},
        json={"subject": "Forbidden", "amount": 10},
        timeout=10,
    )
    assert r.status_code == 403


def test_unknown_outcome_submission_single_attempt(observation, services):
    token = observation.token("paul-buyer")["app_token"]
    client = httpx.Client(base_url=services["business_api"], headers={"Authorization": f"Bearer {token}"}, timeout=10)
    draft_id = client.post("/purchase-requests/drafts", json={"subject": "Failure test", "amount": 15}).json()["id"]
    observation.arm_failure("unknown_outcome", True)
    r = client.post(f"/drafts/{draft_id}/submit")
    assert r.status_code == 504
    # No submitted request.
    assert observation.state(draft_id)["draft"]["submitted"] == 0
    observation.arm_failure("unknown_outcome", False)


def test_median_refused(business_client):
    r = business_client.post("/sources/orders/query", json={"aggregate": "median"})
    assert r.status_code == 200
    data = r.json()
    assert data["refused"] is True
    assert "total" in data["available_aggregates"]


def test_grouping_by_supplier_and_month(observation, services):
    observation.reset("volume")
    token = observation.token("leo-controller")["app_token"]
    client = httpx.Client(base_url=services["business_api"], headers={"Authorization": f"Bearer {token}"}, timeout=10)
    data = client.post("/sources/invoices/query", json={"aggregate": "total", "group_by": ["supplier_id", "month"]}).json()
    groups = {(r["group"]["supplier_id"], r["group"]["month"]): r["total"] for r in data["rows"]}
    assert {s for s, _ in groups} == {"F-PAPETERIE", "F-BUREAU", "F-TRANSIT"}
    assert len({m for _, m in groups}) >= 3
    total = client.post("/sources/invoices/query", json={"aggregate": "total"}).json()["value"]
    assert round(sum(groups.values()), 2) == total
    by_status = client.post("/sources/invoices/query", json={"aggregate": "count", "group_by": "status"}).json()
    assert all(isinstance(r["group"], str) for r in by_status["rows"])
    refused = client.post("/sources/invoices/query", json={"aggregate": "total", "group_by": ["week"]})
    assert refused.status_code == 400 and "month" in refused.text


def test_observation_catalog(observation):
    catalog = observation.reset("standard")
    assert "CMD-1042" in catalog["cases"]
