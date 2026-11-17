"""Agent gateway: health and test identities."""

import httpx
import pytest

pytestmark = pytest.mark.shell


def test_interface_health(services):
    r = httpx.get(f"{services['interface']}/health", timeout=5)
    assert r.status_code == 200


def test_users_lists_the_seeded_identities(services):
    from business_api.seed_data import USERS

    users = httpx.get(f"{services['interface']}/users", timeout=5).json()["users"]
    assert [(u["user_id"], u["role"], u["organization"]) for u in users] == [(u, r, o) for u, _, r, o in USERS]
