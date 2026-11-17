"""Checks of workshop 10a, shared by the public and the private tests (one function per criterion).

Contract read here:
- the business application's call log (`user_id`, `role`, `code`): the API only accepts an
  `application` token; the interface hands the agent an `entry` token (`app_token` of
  `POST /conversations`), which must be exchanged, never relayed as is nor replaced by a token
  the agent issues itself from the declared `user_id`;
- trace `identity` ({`user`, `token_type`: "application"}) and `tools[].result.status`
  ("denied" or "error" when the identity cannot be established);
- the MCP server of `my-agent/mcp_server.py` (workshop 09) reads the entry token from the HTTP
  header `Authorization: Bearer <entry token>`; without it, or with an invalid token, its
  generic tool (input schema with `source` and `filters`) reads nothing.
"""

import asyncio

import jwt
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from business_api.auth import issue_token
from agent_gateway.loader import load_mcp_server
from agent_testkit.chat_client import ChatClient
from agent_testkit.expect import mentions_any, mentions_none
from agent_testkit.servers import free_port, start_uvicorn, wait_for_port
from agent_testkit.turns import business_log, successful_turn, tool_status, tools

DATA_ROUTES = ("/orders", "/sources", "/customers", "/invoices")


def data_log(observation) -> list[dict]:
    return [e for e in business_log(observation) if str(e.get("route", "")).startswith(DATA_ROUTES)]


def forged_entry_token(forged: dict) -> str:
    """Well-formed entry token for `forged["sub"]`, signed with a key the application does not know."""
    claims = {"sub": forged["sub"], "role": forged["role"], "organization": forged["organization"], "typ": "entry"}
    return jwt.encode(claims, forged["key"], algorithm="HS256")


def serve_mcp_server():
    """Body of the `mcp_server_url` fixture: serves `my-agent/mcp_server.py`, yields its URL."""
    module = load_mcp_server()
    port = free_port()
    server = start_uvicorn(module.application(), port)
    wait_for_port("127.0.0.1", port)
    url = f"http://127.0.0.1:{port}{module.MCP_PATH}"
    # Same variable as `workshop serve`: the harness reaches this server through MCP_URL.
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("MCP_URL", url)
        yield url
    server.should_exit = True


def call_generic_tool(url: str, authorization: str | None, arguments: dict):
    async def _run():
        headers = {"Authorization": authorization} if authorization else None
        async with create_mcp_http_client(headers=headers) as http:
            async with streamable_http_client(url, http_client=http) as streams:
                async with ClientSession(streams[0], streams[1]) as session:
                    await session.initialize()
                    tools_ = (await session.list_tools()).tools
                    generic = [t for t in tools_ if {"source", "filters"} <= set((getattr(t, "inputSchema", None) or getattr(t, "input_schema", None) or {}).get("properties", {}))]
                    assert generic, "the MCP server exposes the generic query tool of workshop 09"
                    return await session.call_tool(generic[0].name, arguments)

    return asyncio.run(_run())


def token_exchange(services, observation, case: dict) -> None:
    user = case["user"]
    token = observation.token(user)
    client = ChatClient(services["interface"])
    client.open(**case["open"], app_token=token["entry_token"])
    turn, trace = successful_turn(client, case["question"])
    log = data_log(observation)
    assert log, "the application must receive a call on behalf of the user"
    assert {e.get("user_id") for e in log} == {user}, "every call is made with the user's identity"
    assert all(e.get("code") == 200 for e in log), "the entry token was exchanged for an application token"
    identity = trace.get("identity") or {}
    assert identity.get("user") == user and identity.get("token_type") == "application", (
        "trace.identity records the user and the exchanged token type"
    )
    mentions_any(turn, case["answer_status"], "the answer gives the status read as the user")


def request_without_identity_refused(services, observation, scenario: dict, case: dict) -> None:
    app_token = scenario["app_token"]
    if app_token == "forged":
        app_token = forged_entry_token(scenario["forged"])
    client = ChatClient(services["interface"])
    client.open(**scenario["open"], app_token=app_token)
    before = len(data_log(observation)) if case["only_calls_of_this_turn"] else 0
    turn, trace = successful_turn(client, case["question"])
    assert not any(e.get("code") == 200 for e in data_log(observation)[before:]), (
        "no data is read without a valid entry token: the agent never issues a token itself from the declared user"
    )
    statuses = {tool_status(c) for c in tools(trace)}
    assert statuses and statuses <= {"denied", "error"}, "the refusal is recorded in the tool result (status denied)"
    mentions_none(turn, case["hidden_status"], "nothing read without identity is disclosed")


def other_organization_sees_nothing(services, observation, case: dict) -> None:
    user = case["user"]
    client = ChatClient(services["interface"])
    token = issue_token(user["user_id"], user["role"], user["organization"], typ="entry")
    client.open(**user, app_token=token)
    turn, _ = successful_turn(client, case["question"])
    log = data_log(observation)
    assert log and {e.get("user_id") for e in log} == {user["user_id"]}, "the call is made as the organization-b user"
    mentions_none(turn, case["never_disclosed"], "an order of another organization is never disclosed")


def mcp_server_requires_the_entry_token(mcp_server_url, observation, case: dict) -> None:
    user = case["user"]
    token = observation.token(user)["entry_token"]
    call_generic_tool(mcp_server_url, f"Bearer {token}", case["arguments"])
    log = data_log(observation)
    assert log and all(e.get("code") == 200 and e.get("user_id") == user for e in log), (
        "with the entry token in the Authorization header, the server reads as the user"
    )
    before = len(data_log(observation))
    forged = forged_entry_token(case["forged"])
    for authorization in case["invalid_authorizations"]:
        if authorization is not None:
            authorization = authorization.format(token=token, forged=forged)
        call_generic_tool(mcp_server_url, authorization, case["arguments"])
    assert not any(e.get("code") == 200 for e in data_log(observation)[before:]), (
        "without a valid entry token, the MCP server reads nothing (it neither relays nor invents an identity)"
    )
