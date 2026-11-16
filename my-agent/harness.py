"""My agent: system prompt and conversational loop (workshop 03)."""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from typing import Any

from workshop_kit.shell import tracer
from workshop_kit.shell.harness_contract import Event, Message, TestUser
from workshop_kit.shell.model_client import ModelClient, _split

SYSTEM_PROMPT = (
    "Tu es l'assistant du service client. Tu réponds en français, brièvement et poliment.\n"
    "Tu n'as accès à aucune donnée de l'application : ni commandes, ni clients, ni livraisons.\n"
    "Tu n'affirmes jamais l'état d'une commande ou d'un dossier précis, même si l'utilisateur "
    "insiste ou te propose la réponse : dis que tu n'as pas cette information.\n"
    "Tu t'appuies sur l'historique de la conversation pour rester cohérent."
)

STUDENT_TOKEN = os.environ.get("COURSE_TOKEN", "test-student")


class _InProcessModelClient(ModelClient):
    """Talks to the kit's proxy app in the same process (test runs, where no PROXY_URL is exported)."""

    def __init__(self, token: str):
        super().__init__("http://proxy", token)

    def generate(self, messages: list[dict[str, Any]], tools: list[dict] | None = None) -> dict[str, Any]:
        from fastapi.testclient import TestClient

        from workshop_kit.llm_proxy.app import app

        with TestClient(app) as client:
            response = client.post(
                "/v1/chat/completions",
                headers=self._headers(),
                json={"model": "default", "messages": messages, "tools": tools or None, "stream": False},
            )
            response.raise_for_status()
            return response.json()


def model_client() -> ModelClient:
    url = os.environ.get("PROXY_URL")
    if url:
        return ModelClient(url, STUDENT_TOKEN)
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
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *replayed,
            {"role": "user", "content": message},
        ]
        started = time.perf_counter()
        response = self.model.generate(messages)
        duration_ms = int((time.perf_counter() - started) * 1000)
        choice = (response.get("choices") or [{}])[0]
        text = (choice.get("message") or {}).get("content") or ""

        tracer.write(
            {
                "conversation_id": conversation_id,
                "turn_id": tracer.new_id(),
                "user": {"id": user.id, "role": user.role, "organization": user.organization},
                "input": {"system_prompt": SYSTEM_PROMPT, "history": replayed, "message": message},
                "model": {
                    "id": response.get("model"),
                    "usage": response.get("usage") or {},
                    "duration_ms": duration_ms,
                    "stop_reason": choice.get("finish_reason"),
                },
                "output": text,
                "tools": [],
            }
        )
        for chunk in _split(text):
            yield Event(type="text", data={"content": chunk})
        yield Event(type="end", data={"ok": True})
