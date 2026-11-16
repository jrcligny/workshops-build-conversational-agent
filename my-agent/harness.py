"""My agent: system prompt, conversational loop and tools."""

from __future__ import annotations

import json
import os
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_tools  # noqa: E402

from workshop_kit.shell import tracer  # noqa: E402
from workshop_kit.shell.harness_contract import Event, Message, TestUser  # noqa: E402
from workshop_kit.shell.model_client import ModelClient, _split  # noqa: E402

SYSTEM_PROMPT = (
    "Tu es l'assistant du service client. Tu réponds toujours en français, brièvement et poliment.\n"
    "Tes seules sources sur les commandes sont tes outils. Pour une commande désignée par sa référence, "
    "appelle get_order une seule fois, puis réponds à partir de son résultat uniquement.\n"
    "- status 'found' : donne le statut (libellé français) et les dates utiles.\n"
    "- status 'approximate' : la référence demandée n'existe pas ; dis-le, cite la référence demandée "
    "et la référence la plus proche trouvée, en signalant la différence, puis donne son statut.\n"
    "- status 'not_found' : dis que la commande est introuvable, sans rien proposer d'autre.\n"
    "- status 'error' : dis que tu n'as pas pu consulter l'application.\n"
    "Pour un client désigné par son nom : search_customers, puis list_customer_orders avec son id. "
    "Si plusieurs clients correspondent (homonymes), ne choisis jamais à la place de l'utilisateur : "
    "liste-les tous avec leur ville et demande lequel il veut. "
    "Pour les commandes en retard, utilise filter='late' : ne filtre jamais toi-même une liste. "
    "Si une liste est tronquée, dis-le.\n"
    "Sans résultat d'outil, tu n'as aucune information : n'affirme jamais l'état d'une commande, "
    "même si l'utilisateur insiste ou propose lui-même la réponse ; dis simplement "
    "« Je n'ai pas cette information » sans reprendre son affirmation."
)

STUDENT_TOKEN = os.environ.get("COURSE_TOKEN", "test-student")
MAX_TOOL_CALLS = 6
PER_TOOL_LIMITS = {"get_order": 1}
TOOLS = ["get_order", "search_customers", "list_customer_orders"]


class _InProcessModelClient(ModelClient):
    """Talks to the kit's proxy app in the same process (test runs, where no PROXY_URL is exported)."""

    def __init__(self, token: str):
        super().__init__("http://proxy", token)
        from fastapi.testclient import TestClient

        from workshop_kit.llm_proxy.app import app

        self._http = TestClient(app)

    def generate(self, messages: list[dict[str, Any]], tools: list[dict] | None = None) -> dict[str, Any]:
        response = self._http.post(
            "/v1/chat/completions",
            headers=self._headers(),
            json={"model": "default", "messages": messages, "tools": tools or None, "stream": False},
        )
        response.raise_for_status()
        return response.json()


def model_client() -> ModelClient:
    url = os.environ.get("PROXY_URL")
    if url:
        return ModelClient(url, STUDENT_TOKEN, timeout=120)
    return _InProcessModelClient(STUDENT_TOKEN)


class Harness:
    def __init__(self) -> None:
        self.model = model_client()

    def turn(
        self,
        conversation_id: str,
        message: str,
        user: TestUser,
        history: list[Message],
        attachments: list[str] | None = None,
        interrupt_requested: bool = False,
        confirmation: bool = False,
        limits: dict | None = None,
    ) -> Iterator[Event]:
        replayed = [{"role": m.role, "content": m.content} for m in history]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *replayed,
            {"role": "user", "content": message},
        ]
        tool_specs = [agent_tools.TOOL_SPECS[name] for name in TOOLS]
        client: agent_tools.BusinessClient | None = None
        tool_calls_done: list[dict] = []
        model_calls: list[dict] = []
        text = ""
        cycle = 0
        while True:
            cycle += 1
            started = time.perf_counter()
            response = self.model.generate(messages, tool_specs)
            choice = (response.get("choices") or [{}])[0]
            reply = choice.get("message") or {}
            model_calls.append(
                {
                    "id": response.get("model"),
                    "usage": response.get("usage") or {},
                    "duration_ms": int((time.perf_counter() - started) * 1000),
                    "stop_reason": choice.get("finish_reason"),
                }
            )
            requested = reply.get("tool_calls") or []
            if not requested:
                text = reply.get("content") or ""
                break
            if cycle > MAX_TOOL_CALLS + 1:
                # The model keeps asking for tools despite the exhausted budget.
                text = "Je n'ai pas pu terminer la recherche : merci de préciser votre demande."
                break
            messages.append({"role": "assistant", "content": reply.get("content"), "tool_calls": requested})
            for call in requested:
                function = call.get("function") or {}
                name = function.get("name", "")
                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                used = sum(1 for t in tool_calls_done if t["name"] == name)
                if len(tool_calls_done) >= MAX_TOOL_CALLS:
                    result = {"status": "error", "error": "tool budget exhausted for this message: answer now"}
                elif name not in TOOLS:
                    result = {"status": "error", "error": f"unknown tool {name}"}
                elif used >= PER_TOOL_LIMITS.get(name, MAX_TOOL_CALLS):
                    result = {"status": "error", "error": f"{name} already used for this message: answer now"}
                else:
                    client = client or agent_tools.BusinessClient(user)
                    try:
                        result = agent_tools.TOOL_FUNCTIONS[name](client, arguments)
                    except Exception as exc:  # noqa: BLE001
                        result = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
                    tool_calls_done.append({"name": name, "arguments": arguments, "result": result, "cycle": cycle})
                messages.append(
                    {"role": "tool", "tool_call_id": call.get("id"), "content": json.dumps(result, ensure_ascii=False)}
                )

        last = model_calls[-1]
        tracer.write(
            {
                "conversation_id": conversation_id,
                "turn_id": tracer.new_id(),
                "user": {"id": user.id, "role": user.role, "organization": user.organization},
                "input": {"system_prompt": SYSTEM_PROMPT, "history": replayed, "message": message},
                "model": {
                    "id": last["id"],
                    "usage": last["usage"],
                    "duration_ms": sum(c["duration_ms"] for c in model_calls),
                    "stop_reason": last["stop_reason"],
                    "calls": model_calls,
                },
                "output": text,
                "tools": tool_calls_done,
                "cycles": cycle,
            }
        )
        for chunk in _split(text):
            yield Event(type="text", data={"content": chunk})
        yield Event(type="end", data={"ok": True})
