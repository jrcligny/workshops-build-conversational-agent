"""HTTP/SSE adapter tests; no agent, model, or running server required."""

import json

import httpx
import pytest
from workshop_chat_ui.backend import (
    DEFAULT_BACKEND_URL,
    BackendClient,
    BackendError,
    agent_error,
    configured_url,
    parse_events,
)


def client(handler):
    return BackendClient("http://backend.test/prefix", transport=httpx.MockTransport(handler))


def sse(*events):
    body = "".join(f"event: {kind}\ndata: {json.dumps(data)}\n\n" for kind, data in events)
    return httpx.Response(200, text=body, headers={"Content-Type": "text/event-stream; charset=utf-8"})


def test_url_configuration(monkeypatch):
    monkeypatch.delenv("WORKSHOP_CHAT_BACKEND_URL", raising=False)
    assert configured_url() == DEFAULT_BACKEND_URL
    monkeypatch.setenv("WORKSHOP_CHAT_BACKEND_URL", "http://custom.test/api/")
    assert configured_url() == "http://custom.test/api"


@pytest.mark.asyncio
async def test_new_conversations_and_request_contract():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"id": str(len(requests))})

    backend = client(handler)
    assert await backend.create_conversation() == "1"
    assert await backend.create_conversation() == "2"
    assert all(r.url.path == "/prefix/conversations" and r.method == "POST" for r in requests)
    assert all(json.loads(r.content) == {"sign_in": True} for r in requests)


@pytest.mark.asyncio
async def test_text_steps_tools_and_end():
    def handler(request):
        assert request.url.path == "/prefix/conversations/abc/messages"
        assert json.loads(request.content) == {"text": "Bonjour"}
        return sse(
            ("step", {"name": "Recherche"}),
            ("tool_call", {"name": "orders", "arguments": {"id": "CMD-1042"}}),
            ("tool_result", {"name": "orders", "result": {"status": "livrée"}}),
            ("text", {"content": "Bonjour"}),
            ("text", {"content": " !"}),
            ("end", {"ok": True}),
        )

    events = [event async for event in client(handler).turn("abc", "Bonjour")]
    assert [event.type for event in events] == ["step", "tool_call", "tool_result", "text", "text", "end"]
    assert "".join(e.data["content"] for e in events if e.type == "text") == "Bonjour !"


@pytest.mark.asyncio
async def test_multiline_sse_comments_and_unknown_fields():
    async def lines():
        for line in [": ping", "id: 42", "event: step", 'data: {"name":', 'data: "Recherche"}', "", "retry: 1000", 'data: {"x": 1}', ""]:
            yield line

    events = [event async for event in parse_events(lines())]
    assert events[0].type == "step"
    assert events[0].data == {"name": "Recherche"}
    assert events[1].type == "message"


@pytest.mark.asyncio
@pytest.mark.parametrize("body", ["not-json", "[]", '{"id": null}', '{"id": 123}'])
async def test_invalid_creation_response(body):
    with pytest.raises(BackendError, match="invalide"):
        await client(lambda _: httpx.Response(200, text=body)).create_conversation()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [404, 500, 503])
async def test_http_errors_do_not_expose_raw_response(status):
    with pytest.raises(BackendError) as error:
        await client(lambda _: httpx.Response(status, text="sensitive response")).create_conversation()
    assert "sensitive" not in str(error.value)
    assert "introuvable" in str(error.value) if status == 404 else str(status) in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", [httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError])
async def test_network_errors_are_actionable_and_not_retried(exception):
    calls = []

    def handler(request):
        calls.append(request)
        raise exception("sensitive diagnostics", request=request)

    with pytest.raises(BackendError) as error:
        _ = [event async for event in client(handler).turn("abc", "Bonjour")]
    assert len(calls) == 1
    assert "sensitive" not in str(error.value)
    assert "automatique" in str(error.value)


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [
    sse(("text", {"content": "Partiel"})),
    httpx.Response(200, text='event: text\ndata: invalid\n\n', headers={"Content-Type": "text/event-stream"}),
    httpx.Response(200, text='event: text\ndata: []\n\n', headers={"Content-Type": "text/event-stream"}),
    httpx.Response(200, text="not SSE"),
])
async def test_invalid_or_incomplete_stream(response):
    with pytest.raises(BackendError):
        _ = [event async for event in client(lambda _: response).turn("abc", "Bonjour")]


@pytest.mark.asyncio
async def test_empty_harness_error_is_preserved_and_explained():
    events = [event async for event in client(lambda _: sse(
        ("error", {"detail": "Your turn: implement the system prompt (workshop 03)."}),
        ("end", {"ok": False}),
    )).turn("abc", "Bonjour")]
    assert "atelier 03" in agent_error(events[0].data["detail"])
    assert events[-1].data["ok"] is False
    assert "journaux" in agent_error("internal failure")