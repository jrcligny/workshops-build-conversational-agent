"""Private tests of workshop 10a (not given to students): same criteria, other inputs.

Other users (paul-buyer, nina-accountant, omar-buyer-b, ines-service-b), another order
(CMD-2010), a positive read in organization-b (CMD-B-100) and the MCP server called with
another user's entry token.
"""

import asyncio

import jwt
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from business_api.auth import issue_token
from workshop_kit.shell.loader import load_mcp_server
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.servers import free_port, start_uvicorn, wait_for_port
from workshop_tests.testing.turns import business_log, successful_turn, tool_status, tools

pytestmark = pytest.mark.workshop

QUESTION = "La commande CMD-2010 est-elle déjà partie ? Quel est son statut ?"
DATA_ROUTES = ("/orders", "/sources", "/customers", "/invoices")


def _data_log(observation) -> list[dict]:
    return [e for e in business_log(observation) if str(e.get("route", "")).startswith(DATA_ROUTES)]


def _forged_entry_token(user_id: str, role: str) -> str:
    return jwt.encode({"sub": user_id, "role": role, "organization": "organization-a", "typ": "entry"}, "a-key-unknown-to-the-application", algorithm="HS256")


def test_token_exchange_for_another_user(services, observation):
    token = observation.token("paul-buyer")
    client = ChatClient(services["interface"])
    client.open(user_id="paul-buyer", role="buyer", organization="organization-a", app_token=token["entry_token"])
    turn, trace = successful_turn(client, QUESTION)
    log = _data_log(observation)
    assert log, "the application must receive a call on behalf of the user"
    assert {e.get("user_id") for e in log} == {"paul-buyer"}, "every call is made with the user's identity"
    assert all(e.get("code") == 200 for e in log), "the entry token was exchanged for an application token"
    identity = trace.get("identity") or {}
    assert identity.get("user") == "paul-buyer" and identity.get("token_type") == "application"
    assert "expédiée" in turn.text.lower()


@pytest.mark.parametrize(
    ("user_id", "role", "app_token"),
    [
        ("paul-buyer", "buyer", None),
        ("nina-accountant", "accountant", "Bearer abc.def"),
        ("nina-accountant", "accountant", "forged"),
    ],
    ids=["no-token", "malformed", "forged-signature"],
)
def test_request_without_identity_refused(services, observation, user_id, role, app_token):
    if app_token == "forged":
        app_token = _forged_entry_token(user_id, role)
    client = ChatClient(services["interface"])
    client.open(user_id=user_id, role=role, organization="organization-a", app_token=app_token)
    before = len(_data_log(observation))
    turn, trace = successful_turn(client, QUESTION)
    assert not any(e.get("code") == 200 for e in _data_log(observation)[before:]), (
        "no data is read without a valid entry token: the agent never issues a token itself from the declared user"
    )
    statuses = {tool_status(c) for c in tools(trace)}
    assert statuses and statuses <= {"denied", "error"}, "the refusal is recorded in the tool result (status denied)"
    assert "expédiée" not in turn.text.lower()


def test_other_organization_sees_nothing(services, observation):
    client = ChatClient(services["interface"])
    token = issue_token("omar-buyer-b", "buyer", "organization-b", typ="entry")
    client.open(user_id="omar-buyer-b", role="buyer", organization="organization-b", app_token=token)
    turn, _ = successful_turn(client, QUESTION)
    log = _data_log(observation)
    assert log and {e.get("user_id") for e in log} == {"omar-buyer-b"}, "the call is made as the organization-b user"
    assert "expédiée" not in turn.text.lower() and "450" not in turn.text, "an order of another organization is never disclosed"


def test_other_organization_reads_its_own_order(services, observation):
    client = ChatClient(services["interface"])
    token = issue_token("ines-service-b", "customer_service", "organization-b", typ="entry")
    client.open(user_id="ines-service-b", role="customer_service", organization="organization-b", app_token=token)
    turn, _ = successful_turn(client, "Quel est le statut de la commande CMD-B-100 ?")
    log = _data_log(observation)
    assert log and {e.get("user_id") for e in log} == {"ines-service-b"}
    assert any(e.get("code") == 200 for e in log), "the organization-b user reads the orders of organization-b"
    assert "livrée" in turn.text.lower()


@pytest.fixture(scope="module")
def mcp_server_url():
    module = load_mcp_server()
    port = free_port()
    server = start_uvicorn(module.application(), port)
    wait_for_port("127.0.0.1", port)
    url = f"http://127.0.0.1:{port}{module.MCP_PATH}"
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("MCP_URL", url)
        yield url
    server.should_exit = True


def _call_generic_tool(url: str, authorization: str | None):
    async def _run():
        headers = {"Authorization": authorization} if authorization else None
        async with create_mcp_http_client(headers=headers) as http:
            async with streamable_http_client(url, http_client=http) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    tools_ = (await session.list_tools()).tools
                    generic = [t for t in tools_ if {"source", "filters"} <= set((getattr(t, "inputSchema", None) or getattr(t, "input_schema", None) or {}).get("properties", {}))]
                    assert generic, "the MCP server exposes the generic query tool of workshop 09"
                    return await session.call_tool(generic[0].name, {"source": "invoices", "filters": {"status": "pending"}})

    return asyncio.run(_run())


def test_mcp_server_requires_the_entry_token(mcp_server_url, observation):
    token = observation.token("nina-accountant")["entry_token"]
    _call_generic_tool(mcp_server_url, f"Bearer {token}")
    log = _data_log(observation)
    assert log and all(e.get("code") == 200 and e.get("user_id") == "nina-accountant" for e in log), (
        "with the entry token in the Authorization header, the server reads as that user"
    )
    before = len(_data_log(observation))
    for authorization in (None, f"Basic {token}", f"Bearer {_forged_entry_token('nina-accountant', 'accountant')}"):
        _call_generic_tool(mcp_server_url, authorization)
    assert not any(e.get("code") == 200 for e in _data_log(observation)[before:]), (
        "without a valid entry token, the MCP server reads nothing"
    )
