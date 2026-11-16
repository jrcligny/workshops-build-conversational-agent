"""Private test of workshop 17 (not given to students): masked and observable traces on another
turn (another user, a turn that chains several tool calls). The catalog and route tests have
no input to vary and have no private variant.
"""

import pytest

from workshop_tests.testing.chat_client import ChatClient
from workshop_tests.testing.turns import flat, successful_turn, tools

pytestmark = pytest.mark.workshop


def test_masked_and_observable_traces(services, traces):
    client = ChatClient(services["interface"])
    client.open(user_id="nina-accountant", role="accountant", organization="organization-a")
    successful_turn(client, "Trouvez le client Léa Martin de Lille, puis donnez-moi le montant de sa commande CMD-2010.")
    trace = traces.last()
    flat_t = flat(trace).lower()
    assert "authorization" not in flat_t and "bearer " not in flat_t
    assert "azure_openai_api_key" not in flat_t and "eyj" not in flat_t, "no secret or token in the trace"
    model = trace.get("model") or {}
    assert model.get("usage") and "duration_ms" in model and model.get("calls"), "trace.model records usage, duration_ms and calls"
    assert len(model.get("calls") or []) >= 2, "a chained turn records one entry per model call"
    assert len(tools(trace)) >= 2 and all("duration_ms" in c for c in tools(trace)), "each tool call records duration_ms"
