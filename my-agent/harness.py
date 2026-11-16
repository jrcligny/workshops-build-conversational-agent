"""My agent: system prompt, conversational loop and tools."""

from __future__ import annotations

import json
import os
import re
import sys
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import agent_attachments  # noqa: E402
import agent_context  # noqa: E402
import agent_mcp  # noqa: E402
import agent_memory  # noqa: E402
import agent_observability  # noqa: E402
import agent_preferences  # noqa: E402
import agent_sandbox  # noqa: E402
import agent_skills  # noqa: E402
import mcp_server  # noqa: E402

from workshop_kit.shell import tracer  # noqa: E402
from workshop_kit.shell.harness_contract import Event, Message, TestUser  # noqa: E402
from workshop_kit.shell.model_client import ModelClient, ModelUnavailable, _split, model_unavailable  # noqa: E402

SYSTEM_PROMPT_FILE = Path(__file__).with_name("system_prompt.md")


def load_system_prompt() -> str:
    """Read at each turn, so that an edit of system_prompt.md applies to the next message."""
    text = SYSTEM_PROMPT_FILE.read_text(encoding="utf-8")
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()

STUDENT_TOKEN = os.environ.get("COURSE_TOKEN", "test-student")
MAX_TOOL_CALLS = 12
MAX_CYCLES = 5
CYCLE_LIMIT_INSTRUCTION = (
    "Limite de cycles atteinte : tu ne peux plus appeler d'outil. Réponds maintenant avec ce que tu as vérifié, "
    "en commençant par « Réponse partielle » et en disant précisément ce qui n'a pas pu être vérifié."
)
PER_TOOL_LIMITS = {"get_order": 1}
READ_RETRIES = 1
# Bump when system_prompt.md changes meaningfully; the trace also records its hash.
INSTRUCTIONS_VERSION = "instructions-18"
PRIMARY_MODEL = "default"
FALLBACK_MODEL = "fallback"
FALLBACK_NOTICE = "Le modèle principal est indisponible : cette réponse vient du modèle de secours (bascule unique)."
MODEL_DOWN_TEXT = (
    "Le modèle principal est indisponible et le modèle de secours n'a pas pu répondre non plus : je ne peux pas "
    "traiter votre demande pour l'instant. Rien n'a été modifié ; réessayez dans quelques minutes."
)
UNKNOWN_OUTCOME_TEXT = (
    "L'application n'a pas confirmé le résultat de la soumission : elle n'est pas rejouée, pour éviter un doublon. "
    "Vérifiez dans l'application si la demande a bien été enregistrée avant toute nouvelle tentative."
)


class _InProcessModelClient(ModelClient):
    """Talks to the kit's proxy app in the same process (when no PROXY_URL is exported)."""

    def __init__(self, token: str):
        super().__init__("http://proxy", token)
        from fastapi.testclient import TestClient

        from workshop_kit.llm_proxy.app import app

        self._http = TestClient(app)

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = self._http.post(path, headers=self._headers(), json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # noqa: BLE001
            outage = model_unavailable(exc)
            if outage is not None and outage is not exc:
                raise outage from exc
            raise


def model_client() -> ModelClient:
    url = os.environ.get("PROXY_URL")
    if url:
        return ModelClient(url, STUDENT_TOKEN, timeout=120)
    return _InProcessModelClient(STUDENT_TOKEN)


class Harness:
    def __init__(self) -> None:
        self.model = model_client()
        self.compactor = agent_context.Compactor(self._summarize)
        self.memory = agent_memory.WorkingMemory()
        self.drafts: dict[str, dict] = {}
        self.skills: dict[str, dict[str, dict]] = {}
        self.attachments = agent_attachments.Attachments()

    def _versions(self, catalog: list[dict], token: str, system_prompt: str) -> dict:
        """What produced this turn: instructions, tool definitions, skills catalog, document index (read now)."""
        manifest = agent_skills.load_manifest()
        skills = ",".join(f"{s['id']}@{s.get('version')}" for s in manifest.get("skills") or [] if s.get("id"))
        return {
            "instructions": f"{INSTRUCTIONS_VERSION}+{_digest(system_prompt)}",
            "tools": f"{len(catalog)}+{_digest(json.dumps(catalog, sort_keys=True, ensure_ascii=False))}",
            "skills": f"{manifest.get('version')}+{_digest(skills)}",
            "index": self._index_version(token),
        }

    @staticmethod
    def _index_version(token: str) -> str:
        """Read at every turn: the index in use may be rebuilt at any time."""
        try:
            code, body = mcp_server.DocsSearch(f"Bearer {token}").request("GET", "/indexing/state")
        except Exception as exc:  # noqa: BLE001
            return f"unavailable ({type(exc).__name__})"
        if code != 200:
            return f"unavailable (HTTP {code})"
        documents = sorted(
            f"{d.get('document_id')}@{d.get('version')}:{d.get('n')}" for d in (body or {}).get("documents", [])
        )
        return f"{len(documents)}+{_digest(chr(10).join(documents))}"

    def _summarize(self, request: list[dict[str, Any]]) -> str:
        try:
            response = self.model.generate(request, None)
        except Exception:  # noqa: BLE001
            return ""  # no summary rather than a failed turn; compaction is retried on the next turn
        return ((response.get("choices") or [{}])[0].get("message") or {}).get("content") or ""

    def _call(
        self, messages: list[dict[str, Any]], tools: list[dict] | None, calls: list[dict], fallback: dict
    ) -> dict:
        """One model call. On a primary failure, switches ONCE to the fallback for the rest of the turn."""
        started = time.perf_counter()
        context_size = agent_context.size(messages)
        while True:
            model = FALLBACK_MODEL if fallback["used"] else PRIMARY_MODEL
            try:
                response = self.model.generate(messages, tools, model=model)
                break
            except ModelUnavailable as exc:
                if fallback["used"]:
                    fallback["failed"] = exc.reason
                    raise
                fallback.update(used=True, primary_error=exc.reason, switched_at_call=len(calls) + 1)
        choice = (response.get("choices") or [{}])[0]
        calls.append(
            {
                "id": response.get("model"),
                "requested_model": model,
                "usage": response.get("usage") or {},
                "context_size": context_size,
                "duration_ms": int((time.perf_counter() - started) * 1000),
                "stop_reason": choice.get("finish_reason"),
            }
        )
        return choice.get("message") or {}

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
        system_prompt = load_system_prompt()
        replayed, compacted = self.compactor.apply(
            conversation_id, [{"role": m.role, "content": m.content} for m in history]
        )
        if compacted:
            yield Event(type="compaction", data={k: v for k, v in compacted.items() if k != "summary"})
        self.memory.begin_turn(conversation_id)
        remembered = agent_preferences.load(user)
        memory_trace: dict[str, list] = {"loaded": remembered, "written": [], "deleted": []}
        memory_events: list[dict] = []
        state_before = self.memory.get(conversation_id)
        state_text = self.memory.render(conversation_id)
        # The tools live behind the MCP server; the user's token travels with every call and the tool server
        # exchanges it for an application token on behalf of the user.
        token = agent_mcp.user_token(user)
        allowed_writes = mcp_server.allowed_tools(user.role)
        loaded_skills = self.skills.setdefault(conversation_id, {})
        skills_before = [f"{s['id']}@{s['version']}" for s in loaded_skills.values()]
        gated = agent_skills.gated_tools()
        mcp_specs = agent_mcp.tool_specs(token)
        attachment_ids = self.attachments.attach(conversation_id, user.organization, user.id, attachments)
        # Untrusted content entered this turn: no write tool until the end of the turn.
        writes_removed = bool(attachments)
        attachments_read: list[str] = []

        def offered() -> list[dict]:
            # A write tool needs the user's permission AND, when a skill gates it, that skill loaded.
            unlocked = agent_skills.unlocked(loaded_skills)
            specs = [
                spec
                for spec in mcp_specs
                if spec["function"]["name"] not in mcp_server.HARNESS_ONLY_TOOLS
                and (
                    spec["function"]["name"] not in mcp_server.WRITE_PERMISSIONS
                    or (
                        not writes_removed
                        and spec["function"]["name"] in allowed_writes
                        and (spec["function"]["name"] not in gated or spec["function"]["name"] in unlocked)
                    )
                )
            ]
            local = [agent_skills.tool_spec(), *agent_preferences.tool_specs()]
            # Always offered: the harness refuses (denied) any id this conversation did not receive.
            local.append(agent_attachments.tool_spec())
            return [*local, *specs]

        tool_specs = offered()
        tools = {spec["function"]["name"] for spec in tool_specs}
        skill_events: list[dict] = []
        skill_cycles: dict[str, int] = {}

        # A draft is submitted only after the user's gesture in the interface, by the harness, never by the model.
        submission: dict | None = None
        pending = self.drafts.get(conversation_id)
        yielded: list[Event] = []
        if pending and confirmation and not pending["confirmed_at_creation"]:
            yielded.append(
                Event(type="step", data={"cycle": 0, "tool": "submit_draft", "label": "Soumission du brouillon confirmé"})
            )
            outcome = agent_mcp.call(token, "submit_draft", {"draft_id": pending["id"]})
            submission = {"draft": pending, "outcome": outcome, "by": "harness", "on_behalf_of": user.id, "via": "mcp"}
            self.drafts.pop(conversation_id, None)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "system", "content": _permissions_note(user.role, allowed_writes)},
            {"role": "system", "content": agent_preferences.note(remembered)},
            *([{"role": "system", "content": state_text}] if state_text else []),
            *([{"role": "system", "content": agent_skills.render(loaded_skills)}] if loaded_skills else []),
            *([{"role": "system", "content": agent_attachments.attachments_note(attachment_ids)}] if attachment_ids else []),
            *([{"role": "system", "content": _draft_note(pending, submission)}] if pending else []),
            *replayed,
            {"role": "user", "content": message},
        ]
        yield from yielded

        def lookup(customer_id: str) -> dict | None:
            rows = agent_mcp.call(token, "query", {"source": "customers", "filters": {"id": customer_id}}).get("rows")
            return rows[0] if rows else None

        tool_calls_done: list[dict] = []
        model_calls: list[dict] = []
        # What the model could call, one list per model call, in order (workshops 14 and 15).
        offered_tools: list[list[str]] = []
        mentions: list[str] = []
        stop: str | None = None
        text = ""
        cycle = 0
        fallback: dict[str, Any] = {"used": False}
        turn_limits = agent_sandbox.turn_limits(limits)
        turn_started = time.perf_counter()

        call_started = time.perf_counter()

        def record_tool(entry: dict) -> None:
            entry["duration_ms"] = int((time.perf_counter() - call_started) * 1000)
            tool_calls_done.append(entry)

        def interrupted() -> bool:
            return interrupt_requested

        def limit_reached() -> str | None:
            if time.perf_counter() - turn_started >= turn_limits["duration_s"]:
                return "duration"
            if _tokens_used(model_calls) >= turn_limits["token_budget"]:
                return "token_budget"
            return None

        while True:
            if interrupted():
                stop = "interrupted"
                break
            if cycle >= MAX_CYCLES or len(tool_calls_done) >= MAX_TOOL_CALLS:
                # The tool-call budget is the loop's other cap: both end with the same partial answer.
                stop = "cycle_limit"
                break
            stop = limit_reached()
            if stop:
                break
            cycle += 1
            offered_tools.append([spec["function"]["name"] for spec in tool_specs])
            try:
                reply = self._call(messages, tool_specs, model_calls, fallback)
            except ModelUnavailable:
                stop = "model_unavailable"
                break
            requested = reply.get("tool_calls") or []
            if not requested:
                text = reply.get("content") or ""
                stop = "answered"
                break
            messages.append({"role": "assistant", "content": reply.get("content"), "tool_calls": requested})
            # Independent calls requested together run in the same cycle.
            for call in requested:
                call_started = time.perf_counter()
                function = call.get("function") or {}
                name = function.get("name", "")
                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                used = sum(1 for t in tool_calls_done if t["name"] == name)
                if name == "get_order" and all(
                    (t.get("result") or {}).get("status") == "found" for t in tool_calls_done if t["name"] == name
                ):
                    # A review checks orders one by one; only a missed reference stops further lookups.
                    used = 0
                repeated = any(t["name"] == name and t["arguments"] == arguments for t in tool_calls_done)
                if len(tool_calls_done) >= MAX_TOOL_CALLS:
                    result = {"status": "error", "error": "tool budget exhausted for this message: answer now"}
                elif name not in tools:
                    result = {"status": "error", "error": f"unknown tool {name}"}
                elif repeated:
                    result = {"status": "error", "error": "identical call already made in this turn: use its result"}
                elif used >= PER_TOOL_LIMITS.get(name, MAX_TOOL_CALLS):
                    result = {"status": "error", "error": f"{name} already used for this message: answer now"}
                elif name in (agent_preferences.REMEMBER, agent_preferences.FORGET):
                    yield Event(type="step", data={"cycle": cycle, "tool": name, "label": _step_label(name, arguments)})
                    if name == agent_preferences.REMEMBER:
                        result, entry = agent_preferences.remember(
                            user, str(arguments.get("topic", "")), str(arguments.get("value", ""))
                        )
                        if entry:
                            memory_trace["written"].append(entry)
                            memory_events.append({"action": "written", "topic": entry["topic"], "value": entry["value"]})
                    else:
                        result, deleted = agent_preferences.forget(user, arguments.get("topic"))
                        memory_trace["deleted"].extend(deleted)
                        memory_events.extend(
                            {"action": "deleted", "topic": e["topic"], "value": e["value"]} for e in deleted
                        )
                    record_tool(
                        {"name": name, "arguments": arguments, "result": result, "cycle": cycle, "via": "harness",
                         "transport": "harness"}
                    )
                elif name == agent_attachments.READ_ATTACHMENT:
                    yield Event(type="step", data={"cycle": cycle, "tool": name, "label": _step_label(name, arguments)})
                    result = self.attachments.read(
                        conversation_id, user.organization, user.id, str(arguments.get("attachment_id", ""))
                    )
                    if result["status"] == "ok":
                        attachments_read.append(result["attachment_id"])
                        writes_removed = True
                        tool_specs = offered()
                        tools = {spec["function"]["name"] for spec in tool_specs}
                    record_tool(
                        {"name": name, "arguments": arguments, "result": result, "cycle": cycle, "via": "harness"}
                    )
                elif name == agent_skills.LOAD_SKILL:
                    # Skills are loaded by the harness from the versioned catalog, never by the tool server.
                    yield Event(type="step", data={"cycle": cycle, "tool": name, "label": _step_label(name, arguments)})
                    loaded = agent_skills.load(str(arguments.get("skill_id", "")))
                    result = {k: v for k, v in loaded.items()}
                    denied = [t for t in loaded.get("unlocks") or [] if t not in allowed_writes]
                    if loaded["status"] == "loaded" and denied and len(denied) == len(loaded["unlocks"]):
                        # Permission check: the skill only serves writes this user's role may not do.
                        loaded = {"status": "denied", "id": loaded["id"], "version": loaded.get("version")}
                        result = {
                            **loaded,
                            "error": f"permission refusée : le rôle {user.role} ne peut pas utiliser "
                            f"{', '.join(denied)} ; ne prépare rien et dis à l'utilisateur qu'il n'a pas la permission",
                        }
                    if loaded["status"] == "loaded":
                        loaded_skills[loaded["id"]] = loaded
                        skill_cycles[loaded["id"]] = cycle
                        if denied:
                            result["permissions"] = (
                                f"permission refusée : le rôle {user.role} ne peut pas utiliser {', '.join(denied)} ; "
                                "ne prépare rien et dis-le à l'utilisateur"
                            )
                        tool_specs = offered()
                        tools = {spec["function"]["name"] for spec in tool_specs}
                    if writes_removed and loaded.get("unlocks"):
                        result["write_tools"] = "removed until the end of the turn (untrusted content in this turn)"
                    skill_events.append(
                        {"skill": arguments.get("skill_id"), "status": loaded["status"], "version": loaded.get("version"),
                         "cycle": cycle}
                    )
                    record_tool(
                        {"name": name, "arguments": arguments, "result": {k: v for k, v in result.items() if k != "instructions"},
                         "cycle": cycle, "via": "harness"}
                    )
                else:
                    yield Event(type="step", data={"cycle": cycle, "tool": name, "label": _step_label(name, arguments)})
                    result, attempts = _call_tool(token, name, arguments)
                    record_tool(
                        {"name": name, "arguments": arguments, "result": result, "cycle": cycle, "via": "mcp",
                         "transport": "mcp",
                         **({"attempts": attempts} if attempts > 1 else {})}
                    )
                    self.memory.update(conversation_id, name, arguments, result, lookup)
                messages.append(
                    {"role": "tool", "tool_call_id": call.get("id"), "content": json.dumps(result, ensure_ascii=False)}
                )

        if stop == "interrupted":
            mentions.append("Tour interrompu à votre demande.")
            yield Event(type="interruption", data={"cycle": cycle, "calls_done": len(tool_calls_done)})
            text = (
                "Tour interrompu à votre demande : je n'ai lancé aucune nouvelle recherche."
                if not tool_calls_done
                else "Tour interrompu à votre demande : les recherches restantes n'ont pas été lancées."
            )
        elif stop == "cycle_limit":
            # One last call without tools: answer with what was verified, declared partial.
            messages.append({"role": "system", "content": CYCLE_LIMIT_INSTRUCTION})
            offered_tools.append([])
            try:
                reply = self._call(messages, None, model_calls, fallback)
            except ModelUnavailable:
                reply = {"content": "je n'ai pas pu produire la synthèse : modèle principal et modèle de secours indisponibles."}
            text = reply.get("content") or ""
            if "partiel" not in text.lower():
                text = "Réponse partielle (limite de cycles atteinte). " + text
            mentions.append(
                f"Réponse partielle : limite de la boucle atteinte ({MAX_CYCLES} cycles ou {MAX_TOOL_CALLS} appels d'outil)."
            )
        elif stop == "model_unavailable":
            # Single fallback already tried: the turn ends cleanly, without looping on a down model.
            text = MODEL_DOWN_TEXT
            mentions.append("Modèle indisponible : principal en échec, secours en échec ; tour terminé.")
            yield Event(type="interruption", data={"reason": stop, "cycle": cycle, "calls_done": len(tool_calls_done)})
        elif stop in ("duration", "token_budget"):
            # The limit is hard: no further model call, the turn shows what it obtained and what is missing.
            what = (
                f"limite de durée ({turn_limits['duration_s']} s)"
                if stop == "duration"
                else f"limite de budget ({turn_limits['token_budget']} jetons)"
            )
            obtained = [_step_label(t["name"], t["arguments"]) for t in tool_calls_done]
            text = (
                f"Réponse partielle : tour interrompu, {what} atteinte. "
                + (
                    "Obtenu : " + " ; ".join(obtained) + ". "
                    if obtained
                    else "Obtenu : aucune donnée, aucune recherche n'a pu être lancée. "
                )
                + "Manquant : la réponse complète à votre demande n'a pas pu être établie dans cette limite ; "
                "reformulez une demande plus ciblée ou relancez avec une limite plus large."
            )
            mentions.append(f"Tour interrompu : {what} atteinte.")
            yield Event(type="interruption", data={"reason": stop, "cycle": cycle, "calls_done": len(tool_calls_done)})
        truncated = [t for t in tool_calls_done if t["result"].get("truncated")]
        if stop == "answered" and truncated:
            # The data the answer relies on was incomplete: the answer must say so, whatever the model wrote.
            mentions.append("Réponse partielle : certaines listes ont été tronquées par l'application.")
            if not any(word in text.lower() for word in ("partiel", "incomplet")):
                text = "Réponse partielle (liste tronquée par l'application). " + text
        # A draft prepared in this turn waits for the user's gesture: ask for it, and never announce it as done.
        new_drafts = [t["result"]["draft"] for t in tool_calls_done if t["result"].get("status") == "draft"]
        confirmation_request = None
        if new_drafts:
            draft = new_drafts[-1]
            self.drafts[conversation_id] = {
                "id": draft.get("id"),
                "type": draft.get("type"),
                "payload": draft.get("payload"),
                "confirmed_at_creation": bool(confirmation),
            }
            confirmation_request = {
                "draft_id": draft.get("id"),
                "type": draft.get("type"),
                "payload": draft.get("payload"),
                "message": "Brouillon préparé : rien n'est soumis tant que vous ne l'avez pas confirmé.",
            }
            if _announces_done(text):
                text = (
                    "J'ai préparé un brouillon ; il n'est pas encore soumis. "
                    "Confirmez-le avec le bouton de confirmation pour que je le soumette."
                )
        if submission and submission["outcome"].get("status") == "submitted":
            mentions.append("Soumission effectuée après votre confirmation, en votre nom.")
            body = submission["outcome"].get("result") or {}
            reference = body.get("request_id") or body.get("id") if isinstance(body, dict) else None
            if reference and reference not in text:
                text = (text + " " if text else "") + f"Référence de la demande soumise : {reference}."
        if submission and submission["outcome"].get("status") == "unknown_outcome":
            # Never replayed: a second submission could create a duplicate. The user checks in the application.
            mentions.append("Résultat de soumission inconnu : non rejouée, à vérifier dans l'application.")
            if "vérif" not in text.lower():
                text = UNKNOWN_OUTCOME_TEXT + (" " + text if text else "")
        if fallback["used"] and stop != "model_unavailable":
            mentions.append(FALLBACK_NOTICE)
            if not any(w in text.lower() for w in ("secours", "repli", "indisponible")):
                text = "(Modèle principal indisponible : réponse produite par le modèle de secours.) " + text
        text, cited = _cited_passages(text)
        sources = _sources(tool_calls_done, cited)

        last = model_calls[-1] if model_calls else {"id": None, "usage": {}, "stop_reason": None}
        tracer.write(
            agent_observability.mask({
                "conversation_id": conversation_id,
                "turn_id": tracer.new_id(),
                "user": {"id": user.id, "role": user.role, "organization": user.organization},
                "skills": {
                    "active_before": skills_before,
                    "loaded_this_turn": skill_events,
                    "active": [f"{s['id']}@{s['version']}" for s in loaded_skills.values()],
                },
                "skills_loaded": [
                    {"id": s["id"], "version": s["version"], "cycle": skill_cycles.get(s["id"], 0)}
                    for s in loaded_skills.values()
                ],
                "input": {
                    "system_prompt": system_prompt,
                    "memory": agent_preferences.note(remembered),
                    "skills": agent_skills.render(loaded_skills) if loaded_skills else None,
                    "state": state_before,
                    "history": replayed,
                    "message": message,
                },
                "model": {
                    "id": last["id"],
                    "usage": last["usage"],
                    "duration_ms": sum(c["duration_ms"] for c in model_calls),
                    "stop_reason": last["stop_reason"],
                    "calls": model_calls,
                },
                "versions": self._versions(mcp_specs, token, system_prompt),
                "memory": memory_trace,
                **({"fallback": {"from": PRIMARY_MODEL, "to": FALLBACK_MODEL, "reason": fallback["primary_error"],
                                 **({"failed": fallback["failed"]} if fallback.get("failed") else {})}}
                   if fallback["used"] else {}),
                **({"unknown_outcome": {"draft_id": submission["draft"]["id"]}}
                   if submission and submission["outcome"].get("status") == "unknown_outcome" else {}),
                **({"limit_reached": stop} if stop in ("duration", "token_budget") else {}),
                "output": text,
                "transport": "mcp",
                "identity": agent_mcp.identity_record(user, token),
                "tools": tool_calls_done,
                "offered_tools": offered_tools,
                "cycles": cycle,
                "max_cycles": MAX_CYCLES,
                "stop": stop,
                "cycle_limit_reached": stop == "cycle_limit",
                "interrupted": stop == "interrupted",
                "limits": {**turn_limits, "reached": stop if stop in ("duration", "token_budget") else None,
                           "tokens_used": _tokens_used(model_calls)},
                "sandbox": {"policy_active": True, "file_access": False, "egress": "allowlist"},
                "state": self.memory.get(conversation_id),
                "permissions": {"role": user.role, "write_tools": sorted(allowed_writes)},
                "confirmation": bool(confirmation),
                "pending_draft": self.drafts.get(conversation_id),
                "attachments": {
                    "attached": attachment_ids,
                    "read": attachments_read,
                    "writes_removed": writes_removed,
                },
                "sources": sources,
                **({"submission": submission} if submission else {}),
                **({"compaction": compacted} if compacted else {}),
            })
        )
        if compacted:
            mentions.insert(0, "Le début de la conversation a été résumé pour garder le contexte sous contrôle.")
        if not history:
            # What the long-term memory keeps, and that it can be forgotten: said once, when the conversation opens.
            mentions.insert(0, agent_preferences.OPENING_NOTICE)
        for mention in mentions:
            yield Event(type="mention", data={"content": mention})
        for change in memory_events:
            yield Event(type="memory", data=change)
        for chunk in _split(text):
            yield Event(type="text", data={"content": chunk})
        if sources:
            # The displayed sources come from the passages the tool returned, never from the model's text.
            yield Event(type="sources", data={"sources": sources})
        if confirmation_request:
            yield Event(type="confirmation_requested", data=confirmation_request)
        yield Event(type="end", data={"ok": True})


_DRAFT_LABELS = {"purchase_request": "demande d'achat", "invoice_approval": "approbation de facture"}
_WRITE_LABELS = {
    "prepare_purchase_request": "préparer une demande d'achat",
    "prepare_invoice_approval": "préparer l'approbation d'une facture",
}


def _digest(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


_TRANSIENT = ("503", "502", "504", "timeout", "timed out", "unavailable", "connecterror", "readerror")


def _call_tool(token: str, name: str, arguments: dict) -> tuple[dict, int]:
    """Calls an MCP tool. A read may be retried once on a transient failure; a write is never replayed."""
    retryable = name not in mcp_server.WRITE_PERMISSIONS and name not in mcp_server.HARNESS_ONLY_TOOLS
    attempts = 0
    while True:
        attempts += 1
        try:
            result = agent_mcp.call(token, name, arguments)
        except Exception as exc:  # noqa: BLE001
            result = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        transient = result.get("status") == "error" and not result.get("refused") and any(
            marker in json.dumps(result, ensure_ascii=False).lower() for marker in _TRANSIENT
        )
        if not (retryable and transient and attempts < 1 + READ_RETRIES):
            return result, attempts
        time.sleep(0.3)


_SOURCE_MARKER = re.compile(r"\s*\[source\s*:\s*([^\]]+)\]", re.IGNORECASE)


def _cited_passages(text: str) -> tuple[str, set[str]]:
    """Removes the [source: id] markers from the answer and returns the cited passage ids."""
    cited: set[str] = set()
    for group in _SOURCE_MARKER.findall(text or ""):
        cited.update(part.strip() for part in re.split(r"[,;]", group) if part.strip())
    return _SOURCE_MARKER.sub("", text or "").strip(), cited


def _sources(tool_calls_done: list[dict], cited: set[str]) -> list[dict]:
    """Documentation sources returned by search_documents in this turn AND cited by the answer, deduplicated.

    The search may rank off-topic passages: a passage the answer does not rely on is never displayed, and a
    cited id the tool did not return is ignored (the model cannot invent a source).
    """
    seen: dict[tuple, dict] = {}
    for call in tool_calls_done:
        if call["name"] != "search_documents":
            continue
        for passage in call["result"].get("passages") or []:
            if passage.get("id") not in cited:
                continue
            key = (passage.get("document_id"), passage.get("version"), passage.get("section"))
            seen.setdefault(
                key,
                {
                    "document_id": passage.get("document_id"),
                    "title": passage.get("title"),
                    "section": passage.get("section"),
                    "version": passage.get("version"),
                    "address": passage.get("address"),
                    "passage_id": passage.get("id"),
                },
            )
    return list(seen.values())


def _tokens_used(model_calls: list[dict]) -> int:
    total = 0
    for call in model_calls:
        usage = call.get("usage") or {}
        total += usage.get("total_tokens") or (usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0))
    return total


def _permissions_note(role: str, allowed: set[str]) -> str:
    can = [label for tool, label in _WRITE_LABELS.items() if tool in allowed]
    cannot = [label for tool, label in _WRITE_LABELS.items() if tool not in allowed]
    lines = [f"Droits d'écriture de l'utilisateur (rôle {role}) :"]
    if can:
        lines.append("- il peut " + " et ".join(can) + " : prépare uniquement un brouillon ; la soumission se fait "
                     "après son geste de confirmation dans l'interface. N'annonce jamais une action comme faite "
                     "(« soumise », « envoyée », « approuvée ») tant qu'elle n'a pas été soumise.")
    if cannot:
        lines.append("- il n'a pas la permission de " + " ni de ".join(cannot) + " : s'il le demande, réponds en "
                     "commençant par « Vous n'avez pas la permission de … » et précise qu'aucun brouillon n'a été "
                     "préparé.")
    return "\n".join(lines)


def _draft_note(pending: dict, submission: dict | None) -> str:
    label = _DRAFT_LABELS.get(pending.get("type"), "action")
    if submission:
        outcome = submission["outcome"]
        if outcome.get("status") == "submitted":
            return (f"Le brouillon de {label} {pending['id']} vient d'être soumis par le harnais après le geste de "
                    f"confirmation de l'utilisateur, en son nom. Résultat de l'application : "
                    f"{json.dumps(outcome.get('result'), ensure_ascii=False)}. Annonce-le simplement.")
        if outcome.get("status") == "unknown_outcome":
            return (f"La soumission du brouillon de {label} {pending['id']} a un résultat INCONNU (l'application n'a "
                    "pas répondu à temps) : elle n'est pas rejouée. Ne dis ni qu'elle est faite ni qu'elle a échoué ; "
                    "demande à l'utilisateur de vérifier dans l'application si elle a été enregistrée.")
        return (f"La soumission du brouillon de {label} {pending['id']} n'a pas abouti : "
                f"{json.dumps(outcome, ensure_ascii=False)}. Dis-le sans prétendre qu'elle est faite.")
    return (f"Brouillon de {label} {pending['id']} en attente ({json.dumps(pending.get('payload'), ensure_ascii=False)}) : "
            "il n'est PAS soumis. Il ne le sera qu'après un clic sur le bouton de confirmation de l'interface ; "
            "un message écrit ne suffit pas.")


_DONE_WORDS = ("j'ai soumis", "j'ai envoyé", "a été envoyée", "a été soumise", "est soumise", "c'est soumis",
               "soumission effectuée", "soumission faite", "a été approuvée", "j'ai approuvé")


def _announces_done(text: str) -> bool:
    lowered = text.lower().replace("’", "'")
    return any(word in lowered for word in _DONE_WORDS)


def _step_label(name: str, arguments: dict) -> str:
    labels = {
        "get_order": "Consultation de la commande {reference}",
        "find_by_name": "Recherche de {name}",
        "describe_source": "Description de la source {source}",
        "query": "Lecture de la source {source}",
        "fetch_url": "Récupération de {url}",
        "search_documents": "Recherche dans la documentation : {query}",
        "load_skill": "Chargement de la skill {skill_id}",
        "remember_preference": "Mémorisation de la préférence {topic}",
        "forget_preferences": "Oubli des préférences retenues",
        "read_attachment": "Lecture de la pièce jointe {attachment_id}",
        "prepare_purchase_request": "Préparation du brouillon de demande d'achat",
        "prepare_invoice_approval": "Préparation du brouillon d'approbation de la facture {invoice}",
    }
    try:
        return labels.get(name, name).format(**arguments)
    except (KeyError, IndexError):
        return name
