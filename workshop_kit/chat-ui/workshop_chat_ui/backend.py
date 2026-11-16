"""Async HTTP/SSE adapter, independent of Chainlit and of the agent implementation."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from contextlib import aclosing
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"


class BackendError(Exception):
    """An actionable, user-facing error (never a raw HTTP response or credential)."""


@dataclass(frozen=True)
class Event:
    type: str
    data: dict[str, Any]


@dataclass(frozen=True)
class Identity:
    """A test user of the seeded datasets, as listed by GET /users."""

    user_id: str
    name: str
    role: str
    organization: str

    @property
    def label(self) -> str:
        return f"{self.name} · {self.role} · {self.organization}"


def configured_url() -> str:
    return os.environ.get("WORKSHOP_CHAT_BACKEND_URL", DEFAULT_BACKEND_URL).rstrip("/")


def agent_error(detail: str) -> str:
    if any(word in detail.lower() for word in ("notimplemented", "not implemented", "workshop 03", "system prompt")):
        return (
            "L’agent n’est pas encore implémenté. Réalisez l’atelier 03 dans "
            "my-agent/harness.py, puis redémarrez le backend."
        )
    return "L’agent a rencontré une erreur. Consultez les journaux du backend."


async def parse_events(lines: AsyncIterator[str]) -> AsyncIterator[Event]:
    """Parse SSE frames, including comments, CRLF and multiline JSON data."""
    event_type = "message"
    data: list[str] = []
    async for line in lines:
        if line == "":
            if data:
                try:
                    payload = json.loads("\n".join(data))
                except ValueError as exc:
                    raise BackendError("Réponse SSE invalide du backend (JSON incorrect).") from exc
                if not isinstance(payload, dict):
                    raise BackendError("Réponse SSE invalide du backend (objet attendu).")
                yield Event(event_type, payload)
            event_type, data = "message", []
        elif not line.startswith(":"):
            field, _, value = line.partition(":")
            value = value.removeprefix(" ")
            if field == "event":
                event_type = value
            elif field == "data":
                data.append(value)
    # SSE dispatches only complete frames. The caller also requires an end event.


class BackendClient:
    def __init__(self, base_url: str | None = None, *, transport=None):
        self.base_url = (base_url or configured_url()).rstrip("/") + "/"
        self.transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            transport=self.transport,
            timeout=httpx.Timeout(120.0, connect=5.0),
        )

    @staticmethod
    def _http_error(exc: httpx.HTTPError) -> BackendError:
        if isinstance(exc, httpx.HTTPStatusError):
            if exc.response.status_code == 404:
                return BackendError(
                    "Conversation ou route introuvable. Vérifiez l’URL du backend, "
                    "puis démarrez une nouvelle conversation."
                )
            return BackendError(f"Le backend a renvoyé une erreur HTTP {exc.response.status_code}.")
        if isinstance(exc, httpx.TimeoutException):
            return BackendError(
                "Le backend ne répond pas dans le délai prévu. Le message n’a pas été renvoyé "
                "automatiquement ; vérifiez son état avant de réessayer."
            )
        return BackendError(
            "Connexion au backend impossible ou interrompue. Vérifiez qu’il est démarré "
            "et que WORKSHOP_CHAT_BACKEND_URL est correcte. Aucun renvoi automatique n’a été effectué."
        )

    async def list_users(self) -> list[Identity]:
        try:
            async with self._client() as client:
                response = await client.get("users")
                response.raise_for_status()
                return [
                    Identity(u["user_id"], u.get("name") or u["user_id"], u["role"], u["organization"])
                    for u in response.json()["users"]
                ]
        except httpx.HTTPError as exc:
            raise self._http_error(exc) from exc
        except (ValueError, KeyError, TypeError) as exc:
            raise BackendError("Réponse du backend invalide : liste d’utilisateurs attendue.") from exc

    async def create_conversation(self, identity: Identity | None = None) -> str:
        body: dict[str, Any] = {"sign_in": True}
        if identity is not None:
            body |= {"user_id": identity.user_id, "role": identity.role, "organization": identity.organization}
        try:
            async with self._client() as client:
                response = await client.post("conversations", json=body)
                response.raise_for_status()
                payload = response.json()
                conversation_id = payload.get("id") if isinstance(payload, dict) else None
                if not isinstance(conversation_id, str) or not conversation_id:
                    raise BackendError("Réponse du backend invalide : identifiant de conversation absent.")
                return conversation_id
        except httpx.HTTPError as exc:
            raise self._http_error(exc) from exc
        except ValueError as exc:
            raise BackendError("Réponse du backend invalide : JSON attendu.") from exc

    async def turn(self, conversation_id: str, text: str) -> AsyncIterator[Event]:
        try:
            async with (
                self._client() as client,
                client.stream(
                    "POST",
                    f"conversations/{conversation_id}/messages",
                    json={"text": text},
                    headers={"Accept": "text/event-stream"},
                ) as response,
                aclosing(response.aiter_lines()) as lines,
                aclosing(parse_events(lines)) as events,
            ):
                response.raise_for_status()
                if response.headers.get("content-type", "").split(";")[0] != "text/event-stream":
                    raise BackendError("Réponse du backend invalide : flux SSE attendu.")
                async for event in events:
                    yield event
                    if event.type == "end":
                        return
                raise BackendError(
                    "La réponse a été interrompue avant sa fin. Le message n’a pas été renvoyé automatiquement."
                )
        except httpx.HTTPError as exc:
            raise self._http_error(exc) from exc