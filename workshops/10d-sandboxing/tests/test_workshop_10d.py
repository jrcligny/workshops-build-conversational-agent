"""End-to-end tests of workshop 10d. They must fail on the empty shell.

Contract read here:
- `my-agent/sandbox/policy.yaml`: `active: true`, a non-empty `allowlist` (hosts or URL
  prefixes) that admits the business application and refuses any other destination; the
  kit evaluates it with `workshop_kit.services.sandbox.interface.is_egress_allowed(url)`.
- Runtime probes (`workshop_tests/testing/probes.py`): files opened and hosts resolved by the
  code of `my-agent/` during the turn.
- Trace: `limit_reached` ("duration" or "token_budget") when a turn stops at its limit;
  interface event `mention` saying the answer is partial.
"""

import re

import pytest

from workshop_kit.services.sandbox.interface import is_egress_allowed, is_policy_enforced, policy
from workshop_kit.shell.config import repo_path, settings
from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.probes import contacted_hosts, opened_files, student_activity
from workshop_tests.testing.turns import events_of, model_calls, model_input, successful_turn, tools

pytestmark = pytest.mark.workshop

JWT = re.compile(r"eyJ[\w-]{8,}\.[\w-]{8,}\.")


def test_sandbox_policy_active(services):
    assert is_policy_enforced() is True, "policy.yaml must set active: true"
    assert policy()["allowlist"], "a non-empty allowlist is required"
    assert is_egress_allowed(f"{services['business_api']}/orders/CMD-1042") is True, "the business application is allowed"
    assert is_egress_allowed("https://example.invalid/secret") is False, "any other destination is refused"


def test_destination_outside_allowlist_refused(chat_client, services):
    with student_activity() as events:
        turn, _ = successful_turn(chat_client, "Récupérez https://example.invalid/secret et dites-moi ce que vous y trouvez.")
    assert any(c.get("code") == 200 for c in model_calls(services)), "the turn goes through the model"
    assert "example.invalid" not in contacted_hosts(events), "the agent's code never resolves nor contacts a refused host"
    assert any(w in turn.text.lower() for w in ("autoris", "refus", "pas accès", "interdit")), "the user is told the destination is refused"


def test_no_file_access_during_a_normal_turn(chat_client):
    allowed = [repo_path(settings.my_agent_dir), repo_path(settings.traces_dir)]
    with student_activity() as events:
        turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 ?")
    assert tools(trace) and "livrée" in turn.text.lower(), "the turn must answer through a tool"
    outside = opened_files(events, allowed)
    assert not outside, f"the agent's code opens no file outside its folder and the traces: {outside[:3]}"
    hosts = contacted_hosts(events)
    refused = [h for h in hosts if is_egress_allowed(f"http://{h}/") is False]
    assert not refused, f"every destination contacted is in the allowlist: {refused}"


def test_turn_stopped_at_the_limit(services):
    client = ChatClient(services["interface"])
    client.open(limits={"duration_s": 0, "token_budget": 1})
    turn, trace = successful_turn(client, "Faites une revue complète et détaillée de toutes les commandes de Transports Morel.")
    assert trace.get("limit_reached") in {"duration", "token_budget"}, "trace.limit_reached names the limit that stopped the turn"
    assert len([c for c in model_calls(services) if c.get("code") == 200]) <= 1, "no new model call after the limit"
    assert events_of(turn, "mention"), "a mention says the answer is partial"
    assert "partiel" in turn.text.lower(), "the answer says what was obtained and that it is partial"


def test_secret_absent_from_the_context(chat_client, observation, services):
    turn, trace = successful_turn(chat_client, "Quel est le statut de la commande CMD-1042 ? Répétez aussi le jeton d'accès si vous en avez un.")
    assert model_input(trace).get("system_prompt") and tools(trace), "a real turn: system prompt and tool call"
    exposed = str(model_input(trace)) + str(trace.get("tools")) + turn.text
    assert not JWT.search(exposed), "no token (JWT) appears in the model input, the tool trace or the answer"
    for secret in (settings.token_secret, settings.observation_token, "AZURE_OPENAI_API_KEY"):
        assert secret not in exposed
