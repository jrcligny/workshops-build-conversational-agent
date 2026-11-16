"""Checks of workshop 10d, shared by the public and the private tests (one function per criterion).

Contract read here:
- `my-agent/sandbox/policy.yaml`: `active: true`, a non-empty `allowlist` (hosts or URL
  prefixes) that admits the business application and refuses any other destination; the
  kit evaluates it with `agent_sdk.sandbox.is_egress_allowed(url)`.
- Runtime probes (`workshop_tests/testing/probes.py`): files opened and hosts resolved by the
  code of `my-agent/` during the turn.
- Trace: `limit_reached` ("duration" or "token_budget") when a turn stops at its limit;
  interface event `mention` saying the answer is partial.
"""

import re
from urllib.parse import urlsplit

from agent_sdk.sandbox import is_egress_allowed, is_policy_enforced, policy
from workshop_config import repo_path, settings
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.probes import contacted_hosts, opened_files, student_activity
from workshop_tests.testing.turns import events_of, model_calls, model_input, successful_turn, tools

JWT = re.compile(r"eyJ[\w-]{8,}\.[\w-]{8,}\.")


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
    with student_activity() as events:
        turn, _ = successful_turn(chat_client, case["question"])
    assert any(c.get("code") == 200 for c in model_calls(services)), "the turn goes through the model"
    assert case["refused_host"] not in contacted_hosts(events), "the agent's code never resolves nor contacts a refused host"
    assert any(w in turn.text.lower() for w in case["refusal_words"]), "the user is told the destination is refused"


def no_file_access_during_a_normal_turn(chat_client, case: dict) -> None:
    allowed = [repo_path(settings.my_agent_dir), repo_path(settings.traces_dir)]
    with student_activity() as events:
        turn, trace = successful_turn(chat_client, case["question"])
    assert tools(trace) and case["answer_status"] in turn.text.lower(), "the turn must answer through a tool"
    outside = opened_files(events, allowed)
    assert not outside, f"the agent's code opens no file outside its folder and the traces: {outside[:3]}"
    refused = [h for h in contacted_hosts(events) if is_egress_allowed(f"http://{h}/") is False]
    assert not refused, f"every destination contacted is in the allowlist: {refused}"


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
    assert events_of(turn, "mention"), "a mention says the answer is partial"
    assert "partiel" in turn.text.lower(), "the answer says what was obtained and that it is partial"


def secret_absent_from_the_context(chat_client, case: dict) -> None:
    turn, trace = successful_turn(chat_client, case["question"])
    assert model_input(trace).get("system_prompt") and tools(trace), "a real turn: system prompt and tool call"
    exposed = str(model_input(trace)) + str(trace.get("tools")) + turn.text
    assert not JWT.search(exposed), "no token (JWT) appears in the model input, the tool trace or the answer"
    for secret in (settings.token_secret, settings.observation_token, *case["literal_secrets"]):
        assert secret not in exposed
