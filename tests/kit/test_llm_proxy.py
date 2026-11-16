
import httpx
import pytest

pytestmark = pytest.mark.proxy


def test_sante_mode_simule(services):
    r = httpx.get(f"{services['proxy']}/sante", timeout=5)
    assert r.status_code == 200
    assert r.json()["mode"] == "simule"


def test_sans_jeton_refuse(services):
    r = httpx.post(
        f"{services['proxy']}/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "bonjour"}]},
        timeout=5,
    )
    assert r.status_code == 401


def test_jeton_invente_refuse(services, reset_etat):
    r = httpx.post(
        f"{services['proxy']}/v1/chat/completions",
        headers={"Authorization": "Bearer jeton-invente"},
        json={"messages": [{"role": "user", "content": "bonjour"}]},
        timeout=5,
    )
    assert r.status_code == 401


def test_chat_simule(services, reset_etat):
    r = httpx.post(
        f"{services['proxy']}/v1/chat/completions",
        headers={"Authorization": "Bearer etudiant-essai"},
        json={"messages": [{"role": "user", "content": "Où en est la commande CMD-1042 ?"}]},
        timeout=5,
    )
    assert r.status_code == 200
    texte = r.json()["choices"][0]["message"]["content"]
    assert texte
    # La clé Azure n'apparaît nulle part.
    assert "AZURE" not in texte
    journal = httpx.get(f"{services['proxy']}/journal", headers={"Authorization": "Bearer etudiant-essai"}).json()
    assert journal
    assert all("api_key" not in str(e).lower() and "azure_openai_api_key" not in str(e).lower() for e in journal)


def test_embeddings_deterministes(services, reset_etat):
    def once():
        return httpx.post(
            f"{services['proxy']}/v1/embeddings",
            headers={"Authorization": "Bearer etudiant-essai"},
            json={"input": "livraison incomplète"},
            timeout=5,
        ).json()["data"][0]["embedding"]

    a, b = once(), once()
    assert a == b
    assert len(a) == 64


def test_cle_azure_absente_des_reponses(services, reset_etat):
    r = httpx.get(f"{services['proxy']}/sante", timeout=5)
    corps = r.text.lower()
    assert "sk-" not in corps
    assert reglages_sans_cle(r.json())


def reglages_sans_cle(data: dict) -> bool:
    return "azure_openai_api_key" not in data and not data.get("azure_cle_presente")
