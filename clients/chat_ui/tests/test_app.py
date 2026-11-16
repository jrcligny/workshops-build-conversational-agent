"""Presentation tests with a fake Chainlit session and backend."""

from typing import ClassVar
from unittest.mock import AsyncMock

import pytest
from chat_ui import app
from chat_ui.backend import BackendError, Event, Identity


@pytest.fixture
def ui(monkeypatch):
    session = {}
    messages = []
    steps = []

    class Session:
        get = staticmethod(session.get)
        set = staticmethod(session.__setitem__)

    class Message:
        def __init__(self, content, **kwargs):
            self.content = content
            self.updates = 0
            self.chunks = []

        async def send(self):
            messages.append(self)

        async def update(self):
            self.updates += 1

        async def stream_token(self, content):
            self.chunks.append(content)
            self.content += content

    class Step:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        async def __aenter__(self):
            steps.append(self)
            return self

        async def __aexit__(self, *args):
            pass

    class Backend:
        create_conversation = AsyncMock(side_effect=["first", "second", "third"])
        list_users = AsyncMock(return_value=[])
        events: ClassVar = [Event("text", {"content": "Bonjour !"}), Event("end", {"ok": True})]
        turns: ClassVar = []

        async def turn(self, conversation_id, text):
            self.turns.append((conversation_id, text))
            assert messages[-1].content == "Traitement en cours…"
            for event in self.events:
                if isinstance(event, Exception):
                    raise event
                yield event

    monkeypatch.setattr(app.cl, "user_session", Session)
    monkeypatch.setattr(app.cl, "Message", Message)
    monkeypatch.setattr(app.cl, "Step", Step)
    monkeypatch.setattr(app, "BackendClient", Backend)
    return session, messages, steps, Backend, Message


@pytest.mark.asyncio
async def test_new_chat_replaces_id_and_multiturn_reuses_it(ui):
    session, messages, _, backend, message = ui
    await app.start_chat()
    await app.on_message(message("Bonjour"))
    await app.on_message(message("Encore"))
    assert backend.turns == [("first", "Bonjour"), ("first", "Encore")]
    assert messages[-1].content == "Bonjour !"
    assert messages[-1].updates == 1
    await app.start_chat()
    assert session["conversation_id"] == "second"
    await app.on_message(message("Nouveau"))
    assert backend.turns[-1] == ("second", "Nouveau")


CAMILLE = Identity("camille-renard", "Camille Renard", "customer_service", "organization-a")
PAUL = Identity("paul-buyer", "Paul Morel", "buyer", "organization-a")


@pytest.mark.asyncio
async def test_selected_identity_opens_the_conversation(ui):
    session, messages, _, backend, _ = ui
    backend.list_users = AsyncMock(return_value=[CAMILLE, PAUL])
    profiles = await app.chat_profiles()
    assert [(p.name, p.default) for p in profiles] == [("camille-renard", True), ("paul-buyer", False)]
    session["chat_profile"] = "paul-buyer"
    await app.start_chat()
    backend.create_conversation.assert_awaited_once_with(PAUL)
    assert any("Paul Morel" in m.content for m in messages)
    session["chat_profile"] = "camille-renard"
    await app.start_chat()
    assert backend.create_conversation.await_args.args == (CAMILLE,)
    assert session["conversation_id"] == "second"


@pytest.mark.asyncio
async def test_no_selector_when_users_are_unavailable(ui):
    session, _, _, backend, _ = ui
    backend.list_users = AsyncMock(side_effect=BackendError("down"))
    assert await app.chat_profiles() == []
    await app.start_chat()
    backend.create_conversation.assert_awaited_once_with(None)


@pytest.mark.asyncio
async def test_welcome_is_loaded_from_ui_resource(ui):
    _, messages, _, _, _ = ui
    await app.start_chat()
    expected = app.files("chat_ui").joinpath("welcome.md").read_text(encoding="utf-8")
    assert messages[0].content == expected
    assert "Bonjour, comment puis-je vous aider" in expected
    assert "n’implémente pas les ateliers" not in expected


@pytest.mark.asyncio
async def test_steps_and_tools_are_displayed(ui):
    _, messages, steps, backend, message = ui
    backend.events = [
        Event("step", {"name": "Recherche"}),
        Event("step", {"tool": "orders", "input": {"id": "CMD-1042"}, "output": {"status": "livrée"}}),
        Event("tool_call", {"name": "search", "arguments": {"query": "délai"}}),
        Event("tool_result", {"name": "search", "result": {"count": 2}}),
        Event("text", {"content": "Voici"}),
        Event("text", {"content": " le résultat."}),
        Event("end", {"ok": True}),
    ]
    await app.start_chat()
    await app.on_message(message("Cherche"))
    assert [s.kwargs["type"] for s in steps] == ["run", "tool", "tool", "tool"]
    assert "CMD-1042" in steps[1].input
    assert "livrée" in steps[1].output
    assert messages[-1].content == "Voici le résultat."


@pytest.mark.asyncio
@pytest.mark.parametrize("events, expected", [
    ([Event("error", {"detail": "NotImplementedError: workshop 03"}), Event("end", {"ok": False})], "atelier 03"),
    ([Event("end", {"ok": False})], "journaux"),
    ([BackendError("Connexion impossible")], "Connexion impossible"),
    ([Event("end", {"ok": True})], "sans réponse textuelle"),
])
async def test_errors_and_empty_turn_finish_processing(ui, events, expected):
    _, messages, _, backend, message = ui
    backend.events = events
    await app.start_chat()
    await app.on_message(message("Bonjour"))
    assert expected in messages[-1].content
    assert len(messages) == 2  # welcome + one response, no duplicate error/end
    assert messages[-1].updates == 1


@pytest.mark.asyncio
async def test_backend_initially_unreachable_can_connect_on_next_message(ui):
    session, messages, _, backend, message = ui
    backend.create_conversation.side_effect = [BackendError("Connexion impossible"), "recovered"]
    await app.start_chat()
    assert session["conversation_id"] is None
    assert messages[-1].content == "Connexion impossible"
    await app.on_message(message("Bonjour"))
    assert session["conversation_id"] == "recovered"
    assert messages[-1].content == "Bonjour !"


@pytest.mark.asyncio
async def test_error_after_partial_text_keeps_partial_answer(ui):
    _, messages, _, backend, message = ui
    backend.events = [Event("text", {"content": "Partiel"}), BackendError("Connexion interrompue")]
    await app.start_chat()
    await app.on_message(message("Bonjour"))
    assert messages[-2].content == "Partiel"
    assert messages[-2].updates == 1
    assert messages[-1].content == "Connexion interrompue"