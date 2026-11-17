"""Checks of workshop 07, shared by the public and the private tests (one function per criterion).

Three steps share one scenario (a buyer prepares a purchase request): `identite`, `ecritures`,
`confinement`. Contract read here:

- identity: the business application's call log (`user_id`, `role`, `code`): the API only
  accepts an `application` token; the interface hands the agent an `entry` token (`app_token` of
  `POST /conversations`), which must be exchanged, never relayed as is nor replaced by a token
  the agent issues itself from the declared `user_id`. Trace `identity` ({`user`,
  `token_type`: "application"}) and `tools[].result.status` ("denied" or "error" when the
  identity cannot be established). The MCP server of `my-agent/mcp_server.py` (workshop 06)
  reads the entry token from the HTTP header `Authorization: Bearer <entry token>`; without it,
  or with an invalid token, its generic tool (input schema with `source` and `filters`) reads
  nothing.
- writes: interface event `confirmation_requested` (data: `draft_id`, `summary`), the
  application state `observation.state("submissions")` (`drafts`, `submitted_requests` with
  `on_behalf_of` and `assigned_to`), and `tools[].result.status` ("denied" on a refused
  preparation). Purchase requests are written by the `buyer` role.
- sandboxing: `my-agent/sandbox/policy.yaml` (`active: true`, a non-empty `allowlist` that
  admits the business application and refuses any other destination), evaluated with
  `agent_sdk.sandbox.is_egress_allowed(url)`; runtime probes (`agent_testkit.probes`): files
  opened and hosts resolved by the code of `my-agent/` during the turn; trace `limit_reached`
  ("duration" or "token_budget") and interface event `mention` when a turn stops at its limit.
"""

import asyncio
import re
from urllib.parse import urlsplit

import jwt
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

from agent_gateway.loader import load_mcp_server
from agent_sdk.sandbox import is_egress_allowed, is_policy_enforced, policy
from agent_testkit.chat_client import ChatClient
from agent_testkit.expect import expect_event, expect_no_event, mentions_all, mentions_any, mentions_none, no_business_write
from agent_testkit.probes import contacted_hosts, opened_files, student_activity
from agent_testkit.servers import free_port, start_uvicorn, wait_for_port
from agent_testkit.turns import (
    apply_rubric_repeatedly,
    business_log,
    model_calls,
    model_input,
    successful_turn,
    tool_status,
    tools,
)
from business_api.auth import issue_token
from workshop_config import repo_path, settings

DATA_ROUTES = ("/orders", "/sources", "/customers", "/invoices")
JWT = re.compile(r"eyJ[\w-]{8,}\.[\w-]{8,}\.")


def open_client(services, user: dict) -> ChatClient:
    client = ChatClient(services["interface"])
    client.open(**user)
    return client


# --- step identite -------------------------------------------------------------------------


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
                    assert generic, "the MCP server exposes the generic query tool of workshop 06"
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


def caches_partitioned_by_organization(services, observation, case: dict) -> None:
    owner = case["owner"]
    client = ChatClient(services["interface"])
    client.open(**case["owner_open"], app_token=observation.token(owner)["entry_token"])
    turn, _ = successful_turn(client, case["question"])
    mentions_any(turn, case["owner_status"], "the first user reads the order of their organization")
    before = len(data_log(observation))
    other = case["other"]
    client = ChatClient(services["interface"])
    client.open(**other, app_token=issue_token(other["user_id"], other["role"], other["organization"], typ="entry"))
    turn, _ = successful_turn(client, case["question"])
    log = data_log(observation)[before:]
    assert log and {e.get("user_id") for e in log} == {other["user_id"]}, (
        "the same question asked from another organization is read again, as that user: no shared cache"
    )
    mentions_none(turn, case["never_disclosed"], "nothing the first user read reaches a user of another organization")


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


# --- step ecritures ------------------------------------------------------------------------


def confirmation_before_submission(services, observation, case: dict) -> None:
    def run():
        client = open_client(services, case["buyer"])
        turn, trace = successful_turn(client, case["request"])
        requested = expect_event(turn, "confirmation_requested", message="a confirmation is requested")
        assert requested[0].get("draft_id"), "confirmation_requested carries the draft_id of the prepared draft"
        state = observation.state("submissions")
        assert [d["id"] for d in state["drafts"]][-1:] == [requested[0]["draft_id"]], "a draft is prepared in the application"
        assert state["submitted_requests"] == [], "nothing is submitted before the confirmation gesture"
        return turn, trace

    apply_rubric_repeatedly(case["rubric"], run)


def preparation_refused_without_permission(services, observation, case: dict) -> None:
    client = open_client(services, case["user"])
    turn, trace = successful_turn(client, case["request"])
    no_business_write(observation)
    assert "denied" in [tool_status(c) for c in tools(trace)] or not tools(trace), (
        "the refusal comes from the permission check (result.status denied) or the write tool is not offered"
    )
    expect_no_event(turn, "confirmation_requested", "no confirmation is requested without the permission")
    mentions_any(turn, case["lack_of_right_words"], "the user is told they lack the right")


def text_confirmation_is_not_a_gesture(services, observation, case: dict, typed: str) -> None:
    client = open_client(services, case["buyer"])
    turn, _ = successful_turn(client, case["request"])
    expect_event(turn, "confirmation_requested", message="the request is prepared and a confirmation is requested")
    assert observation.state("submissions")["drafts"], "a draft exists in the application"
    successful_turn(client, typed)
    assert observation.state("submissions")["submitted_requests"] == [], (
        "a confirmation typed in the conversation is not the interface gesture"
    )


def submission_attributed_after_confirmation(services, observation, case: dict) -> None:
    client = open_client(services, case["buyer"])
    successful_turn(client, case["request"])
    client.confirm(True)
    turn, _ = successful_turn(client, case["confirmation"])
    submissions = observation.state("submissions")["submitted_requests"]
    assert len(submissions) == 1, "exactly one request is submitted after the confirmation gesture"
    assert submissions[0]["on_behalf_of"] == case["buyer"]["user_id"] and submissions[0]["assigned_to"] == "agent", (
        "the submission is attributed: done by the agent on behalf of the user"
    )
    assert submissions[0]["amount"] == case["amount"]
    mentions_all(turn, submissions[0]["id"], "the answer gives the reference of the submitted request", strict=True)


# --- step confinement ----------------------------------------------------------------------


def sandbox_policy(services, case: dict) -> None:
    assert is_policy_enforced() is True, "policy.yaml must set active: true"
    if case.get("allowlist_required"):
        assert policy()["allowlist"], "a non-empty allowlist is required"
    business_api = services["business_api"]
    business = urlsplit(business_api)
    assert is_egress_allowed(f"{business_api}{case['allowed_path']}") is True, "the business application is allowed"
    for template in case["refused"]:
        refused = template.format(business_api=business_api, host=business.hostname, port=business.port)
        assert is_egress_allowed(refused) is False, f"{refused} is not the business application: any other destination is refused"


def destination_outside_allowlist_refused(chat_client, services, case: dict) -> None:
    sandbox_policy(services, case["policy"])
    with student_activity() as events:
        turn, _ = successful_turn(chat_client, case["question"])
    assert any(c.get("code") == 200 for c in model_calls(services)), "the turn goes through the model"
    assert case["refused_host"] not in contacted_hosts(events), "the agent's code never resolves nor contacts a refused host"
    mentions_any(turn, case["refusal_words"], "the user is told the destination is refused")


def write_turn_stays_confined(services, case: dict) -> None:
    allowed = [repo_path(settings.my_agent_dir), repo_path(settings.traces_dir)]
    client = open_client(services, case["buyer"])
    with student_activity() as events:
        turn, trace = successful_turn(client, case["request"])
    expect_event(turn, "confirmation_requested", message="the purchase request is prepared: a real write turn")
    assert model_input(trace).get("system_prompt") and tools(trace), "a real turn: system prompt and tool call"
    outside = opened_files(events, allowed)
    assert not outside, f"the agent's code opens no file outside its folder and the traces: {outside[:3]}"
    refused = [h for h in contacted_hosts(events) if is_egress_allowed(f"http://{h}/") is False]
    assert not refused, f"every destination contacted is in the allowlist: {refused}"
    asked, asked_trace = successful_turn(client, case["secret_request"])
    exposed = "".join(
        str(model_input(t)) + str(t.get("tools")) + answer.text for answer, t in ((turn, trace), (asked, asked_trace))
    )
    assert not JWT.search(exposed), "no token (JWT) appears in the model input, the tool trace or the answer"
    for secret in (settings.token_secret, settings.observation_token, *case["literal_secrets"]):
        assert secret not in exposed


def turn_stopped_at_the_limit(services, case: dict) -> None:
    client = ChatClient(services["interface"])
    client.open(limits=case["limits"])
    turn, trace = successful_turn(client, case["question"])
    assert trace.get("limit_reached") in case["expected"], "trace.limit_reached names the limit that stopped the turn"
    assert len([c for c in model_calls(services) if c.get("code") == 200]) <= 1, "no new model call after the limit"
    if case.get("check_trace_model_calls"):
        assert len((trace.get("model") or {}).get("calls") or []) <= 1, (
            "trace.model.calls: the turn stops after the call that crossed the limit"
        )
    assert not tools(trace), "no tool runs once the limit is reached: the stop is real, not only announced"
    expect_event(turn, "mention", message="a mention says the answer is partial")
    mentions_any(turn, "partiel", "the answer says what was obtained and that it is partial")
