"""LLM proxy: course tokens, simulated chat, deterministic embeddings, no Azure key leak."""

import httpx
import pytest

from workshop_kit.shell.config import settings

pytestmark = pytest.mark.llm_proxy

STUDENT = {"Authorization": "Bearer test-student"}


def test_health_reports_configured_mode(services):
    r = httpx.get(f"{services['proxy']}/health", timeout=5)
    assert r.status_code == 200
    assert r.json()["mode"] == (settings.proxy_mode or "simulated").lower()


def test_no_token_refused(services):
    r = httpx.post(
        f"{services['proxy']}/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "bonjour"}]},
        timeout=5,
    )
    assert r.status_code == 401


def test_made_up_token_refused(services, reset_state):
    r = httpx.post(
        f"{services['proxy']}/v1/chat/completions",
        headers={"Authorization": "Bearer made-up-token"},
        json={"messages": [{"role": "user", "content": "bonjour"}]},
        timeout=5,
    )
    assert r.status_code == 401


def test_simulated_chat(services, reset_state):
    r = httpx.post(
        f"{services['proxy']}/v1/chat/completions",
        headers=STUDENT,
        json={"messages": [{"role": "user", "content": "Quel est le statut de la commande CMD-1042 ?"}]},
        timeout=5,
    )
    assert r.status_code == 200
    text = r.json()["choices"][0]["message"]["content"]
    assert text
    # The Azure key appears nowhere.
    assert "AZURE" not in text
    log = httpx.get(f"{services['proxy']}/log", headers=STUDENT).json()
    assert log
    assert all("api_key" not in str(e).lower() and "azure_openai_api_key" not in str(e).lower() for e in log)


def test_deterministic_embeddings(services, reset_state):
    def once():
        return httpx.post(
            f"{services['proxy']}/v1/embeddings",
            headers=STUDENT,
            json={"input": "livraison incomplète"},
            timeout=5,
        ).json()["data"][0]["embedding"]

    a, b = once(), once()
    assert a == b
    assert len(a) == 64


def test_azure_key_absent_from_responses(services, reset_state):
    r = httpx.get(f"{services['proxy']}/health", timeout=5)
    body = r.text.lower()
    assert "sk-" not in body
    data = r.json()
    assert "azure_openai_api_key" not in data and not data.get("azure_key_present")


def test_live_url_from_portal_operation_url(monkeypatch):
    from workshop_kit.llm_proxy import live

    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://res.openai.azure.com/openai/responses?api-version=2025-04-01-preview")
    url, v1 = live._url("chat-dep")
    assert url == "https://res.openai.azure.com/openai/deployments/chat-dep/chat/completions?api-version=2025-04-01-preview"
    assert not v1
    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://res.openai.azure.com/openai/v1/")
    assert live._url("chat-dep") == ("https://res.openai.azure.com/openai/v1/chat/completions", True)


def test_live_mode_without_settings_is_explicit(monkeypatch):
    from workshop_kit.llm_proxy import live

    monkeypatch.setattr(settings, "azure_openai_api_key", "")
    with pytest.raises(live.LiveError) as exc:
        live.chat([{"role": "user", "content": "bonjour"}])
    assert exc.value.status_code == 503
    assert "AZURE_OPENAI_API_KEY" in exc.value.detail