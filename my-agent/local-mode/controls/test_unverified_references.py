"""Checks of the specified control against deliberately wrong model outputs (workshop 17)."""

import importlib.util
from pathlib import Path

_PATH = Path(__file__).resolve().parents[2] / "agent_controls.py"
_SPEC = importlib.util.spec_from_file_location("agent_controls", _PATH)
controls = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(controls)

WRONG_OUTPUT = "La commande CMD-0000 est livrée."


def test_invented_reference_is_flagged():
    flagged = controls.unverified_references(WRONG_OUTPUT, tool_calls=[])
    assert flagged == ["CMD-0000"]
    assert "CMD-0000" in controls.unverified_mention(flagged)


def test_near_reference_is_flagged():
    read = [{"name": "get_order", "arguments": {"reference": "CMD-1042"}, "result": {"status": "found"}}]
    assert controls.unverified_references("CMD-1402 est livrée.", read) == ["CMD-1402"]


def test_several_references_listed_once():
    text = "CMD-0001 et CMD-0002 sont livrées ; CMD-0001 a été payée."
    assert controls.unverified_references(text, []) == ["CMD-0001", "CMD-0002"]


def test_consulted_reference_is_not_flagged():
    read = [{"name": "get_order", "arguments": {"reference": "CMD-1042"},
             "result": {"status": "found", "order": {"reference": "CMD-1042", "status": "delivered"}}}]
    assert controls.unverified_references("La commande CMD-1042 est livrée.", read) == []


def test_reference_from_context_or_summary_is_not_flagged():
    context = [{"role": "tool", "tool_call_id": "c1", "content": '{"rows": [{"reference": "CMD-2010"}]}'}]
    assert controls.unverified_references("CMD-2010 est en retard.", [], context) == []
    assert controls.unverified_references("CMD-3000 est livrée.", [], [], summary="Faits : CMD-3000 livrée.") == []
