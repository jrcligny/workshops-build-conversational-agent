"""Chainlit presentation only: all turns go through the existing conversation API."""

from __future__ import annotations

import asyncio
import json
from importlib.resources import files

import chainlit as cl

from workshop_chat_ui.backend import BackendClient, BackendError, Event, Identity, agent_error


def _display(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2)


async def show_step(event: Event) -> None:
    """Display operational events only, never infer tools from assistant text."""
    data = event.data
    tool = data.get("tool") or data.get("tool_name")
    is_tool = bool(tool) or event.type in {"tool_call", "tool_result"} or data.get("type") == "tool"
    name = str(tool or data.get("name") or data.get("title") or "Étape de l’agent")
    async with cl.Step(name=name, type="tool" if is_tool else "run", show_input="json") as step:
        if "input" in data or "arguments" in data:
            step.input = _display(data.get("input", data.get("arguments")))
        step.output = _display(data.get("output", data.get("result", data)))
        step.language = "json"


async def _users() -> list[Identity]:
    try:
        return await BackendClient().list_users()
    except BackendError:
        return []


def profiles(users: list[Identity]) -> list[cl.ChatProfile]:
    """One chat profile per test identity; Chainlit starts a new chat when the profile changes."""
    return [
        cl.ChatProfile(
            name=user.user_id,
            display_name=user.label,
            markdown_description=f"Converser en tant que **{user.name}** ({user.role}, {user.organization}).",
            default=index == 0,
        )
        for index, user in enumerate(users)
    ]


def selected_identity(users: list[Identity], profile: str | None) -> Identity | None:
    return next((user for user in users if user.user_id == profile), None)


@cl.set_chat_profiles
async def chat_profiles(current_user=None, language=None) -> list[cl.ChatProfile]:
    return profiles(await _users())


@cl.on_chat_start
async def start_chat() -> None:
    # Every Chainlit session/new chat gets a new backend id. No shared global history.
    cl.user_session.set("conversation_id", None)
    identity = selected_identity(await _users(), cl.user_session.get("chat_profile"))
    cl.user_session.set("identity", identity)
    cl.user_session.set("turn_lock", asyncio.Lock())
    await cl.Message(
        author="Atelier",
        content=files("workshop_chat_ui").joinpath("welcome.md").read_text(encoding="utf-8"),
    ).send()
    if identity is not None:
        await cl.Message(author="Atelier", content=f"Identité : **{identity.label}**").send()
    try:
        conversation_id = await BackendClient().create_conversation(identity)
        cl.user_session.set("conversation_id", conversation_id)
    except BackendError as exc:
        await cl.Message(author="Connexion", content=str(exc)).send()


@cl.on_message
async def on_message(message: cl.Message) -> None:
    text = message.content.strip()
    if not text:
        return
    lock = cl.user_session.get("turn_lock")
    if lock is None:
        lock = asyncio.Lock()
        cl.user_session.set("turn_lock", lock)
    async with lock:
        answer = cl.Message(author="Agent", content="Traitement en cours…")
        await answer.send()
        received_text = False
        reported_error = False
        try:
            backend = BackendClient()
            conversation_id = cl.user_session.get("conversation_id")
            if not conversation_id:
                conversation_id = await backend.create_conversation(cl.user_session.get("identity"))
                cl.user_session.set("conversation_id", conversation_id)
            async for event in backend.turn(conversation_id, text):
                if event.type == "text":
                    chunk = event.data.get("content", "")
                    if chunk:
                        if not received_text:
                            answer.content = ""
                            received_text = True
                        await answer.stream_token(str(chunk))
                elif event.type in {"step", "tool_call", "tool_result"}:
                    await show_step(event)
                elif not reported_error and (
                    event.type == "error"
                    or (event.type == "end" and not event.data.get("ok", False))
                ):
                    error = agent_error(str(event.data.get("detail", "")))
                    if received_text:
                        await cl.Message(author="Erreur", content=error).send()
                    else:
                        answer.content = error
                    reported_error = True
            if not received_text and not reported_error:
                answer.content = "Le tour est terminé sans réponse textuelle."
        except BackendError as exc:
            if received_text:
                await cl.Message(author="Erreur", content=str(exc)).send()
            else:
                answer.content = str(exc)
        finally:
            await answer.update()