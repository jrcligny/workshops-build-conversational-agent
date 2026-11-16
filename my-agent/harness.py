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

import agent_context  # noqa: E402
import agent_mcp  # noqa: E402
import agent_memory  # noqa: E402
import mcp_server  # noqa: E402

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
    "Pour un nom (client par défaut, sinon fournisseur ou utilisateur) : find_by_name, puis query avec l'id "
    "trouvé. Quand l'utilisateur passe à un autre client (« passons à X »), recherche-le aussitôt avec "
    "find_by_name. "
    "Si plusieurs clients correspondent (homonymes), ne choisis jamais à la place de l'utilisateur : "
    "liste-les tous avec leur ville et demande lequel il veut, sauf si l'utilisateur a déjà donné un critère "
    "qui en désigne un seul (sa ville, par exemple). Quand il choisit parmi des homonymes, utilise l'id "
    "correspondant. Pour « celle-là », « ce client », appuie-toi sur l'état de la conversation.\n"
    "Toute autre lecture passe par query(source, filters, aggregate) sur orders, customers, invoices, "
    "suppliers ou purchase_requests ; filters est un objet {champ: valeur} (codes ou libellés), "
    "describe_source donne les champs et valeurs. Commandes d'un client : source orders, "
    "filters {customer_id}. Commandes en retard : ajoute \"late\": true dans filters ; ne filtre jamais "
    "toi-même une liste. Pour un nombre, un total ou une moyenne, utilise aggregate (count, total, average) "
    "plutôt qu'une liste. Si une liste est tronquée, dis-le et donne le total. Si un outil renvoie une erreur, "
    "corrige ta requête d'après son message (champs et valeurs autorisés) ; si tu ne peux pas, explique "
    "l'erreur à l'utilisateur en citant les valeurs valides.\n"
    "Enchaîne les outils nécessaires dans le même tour ; demande en une seule fois les appels "
    "indépendants les uns des autres (par exemple une commande et un client).\n"
    "Si un outil répond que la requête est refusée faute d'identité vérifiée, dis que tu n'as pas pu vérifier "
    "l'identité de l'utilisateur et que tu ne peux donc rien consulter en son nom.\n"
    "Sans résultat d'outil, tu n'as aucune information : n'affirme jamais l'état d'une commande, "
    "même si l'utilisateur insiste ou propose lui-même la réponse ; dis simplement "
    "« Je n'ai pas cette information » sans reprendre son affirmation."
)

STUDENT_TOKEN = os.environ.get("COURSE_TOKEN", "test-student")
MAX_TOOL_CALLS = 12
MAX_CYCLES = 5
CYCLE_LIMIT_INSTRUCTION = (
    "Limite de cycles atteinte : tu ne peux plus appeler d'outil. Réponds maintenant avec ce que tu as vérifié, "
    "en commençant par « Réponse partielle » et en disant précisément ce qui n'a pas pu être vérifié."
)
PER_TOOL_LIMITS = {"get_order": 1}


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
        self.compactor = agent_context.Compactor(self._summarize)
        self.memory = agent_memory.WorkingMemory()
        self.drafts: dict[str, dict] = {}

    def _summarize(self, request: list[dict[str, Any]]) -> str:
        response = self.model.generate(request, None)
        return ((response.get("choices") or [{}])[0].get("message") or {}).get("content") or ""

    def _call(self, messages: list[dict[str, Any]], tools: list[dict] | None, calls: list[dict]) -> dict:
        started = time.perf_counter()
        context_size = agent_context.size(messages)
        response = self.model.generate(messages, tools)
        choice = (response.get("choices") or [{}])[0]
        calls.append(
            {
                "id": response.get("model"),
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
        replayed, compacted = self.compactor.apply(
            conversation_id, [{"role": m.role, "content": m.content} for m in history]
        )
        if compacted:
            yield Event(type="compaction", data={k: v for k, v in compacted.items() if k != "summary"})
        state_before = self.memory.get(conversation_id)
        state_text = self.memory.render(conversation_id)
        # The tools live behind the MCP server; the user's token travels with every call and the tool server
        # exchanges it for an application token on behalf of the user.
        token = agent_mcp.user_token(user)
        allowed_writes = mcp_server.allowed_tools(user.role)
        tool_specs = [
            spec
            for spec in agent_mcp.tool_specs(token)
            if spec["function"]["name"] not in mcp_server.HARNESS_ONLY_TOOLS
            and (spec["function"]["name"] not in mcp_server.WRITE_PERMISSIONS or spec["function"]["name"] in allowed_writes)
        ]
        tools = {spec["function"]["name"] for spec in tool_specs}

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
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": _permissions_note(user.role, allowed_writes)},
            *([{"role": "system", "content": state_text}] if state_text else []),
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
        mentions: list[str] = []
        stop: str | None = None
        text = ""
        cycle = 0

        def interrupted() -> bool:
            return interrupt_requested

        while True:
            if interrupted():
                stop = "interrupted"
                break
            if cycle >= MAX_CYCLES:
                stop = "cycle_limit"
                break
            cycle += 1
            reply = self._call(messages, tool_specs, model_calls)
            requested = reply.get("tool_calls") or []
            if not requested:
                text = reply.get("content") or ""
                stop = "answered"
                break
            messages.append({"role": "assistant", "content": reply.get("content"), "tool_calls": requested})
            # Independent calls requested together run in the same cycle.
            for call in requested:
                function = call.get("function") or {}
                name = function.get("name", "")
                try:
                    arguments = json.loads(function.get("arguments") or "{}")
                except json.JSONDecodeError:
                    arguments = {}
                used = sum(1 for t in tool_calls_done if t["name"] == name)
                repeated = any(t["name"] == name and t["arguments"] == arguments for t in tool_calls_done)
                if len(tool_calls_done) >= MAX_TOOL_CALLS:
                    result = {"status": "error", "error": "tool budget exhausted for this message: answer now"}
                elif name not in tools:
                    result = {"status": "error", "error": f"unknown tool {name}"}
                elif repeated:
                    result = {"status": "error", "error": "identical call already made in this turn: use its result"}
                elif used >= PER_TOOL_LIMITS.get(name, MAX_TOOL_CALLS):
                    result = {"status": "error", "error": f"{name} already used for this message: answer now"}
                else:
                    yield Event(type="step", data={"cycle": cycle, "tool": name, "label": _step_label(name, arguments)})
                    try:
                        result = agent_mcp.call(token, name, arguments)
                    except Exception as exc:  # noqa: BLE001
                        result = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
                    tool_calls_done.append(
                        {"name": name, "arguments": arguments, "result": result, "cycle": cycle, "via": "mcp"}
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
            reply = self._call(messages, None, model_calls)
            text = reply.get("content") or ""
            if "partiel" not in text.lower():
                text = "Réponse partielle (limite de cycles atteinte). " + text
            mentions.append(f"Réponse partielle : limite de {MAX_CYCLES} cycles atteinte.")
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

        last = model_calls[-1] if model_calls else {"id": None, "usage": {}, "stop_reason": None}
        tracer.write(
            {
                "conversation_id": conversation_id,
                "turn_id": tracer.new_id(),
                "user": {"id": user.id, "role": user.role, "organization": user.organization},
                "input": {
                    "system_prompt": SYSTEM_PROMPT,
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
                "output": text,
                "transport": "mcp",
                "identity": agent_mcp.identity_record(user, token),
                "tools": tool_calls_done,
                "cycles": cycle,
                "max_cycles": MAX_CYCLES,
                "stop": stop,
                "cycle_limit_reached": stop == "cycle_limit",
                "interrupted": stop == "interrupted",
                "state": self.memory.get(conversation_id),
                "permissions": {"role": user.role, "write_tools": sorted(allowed_writes)},
                "confirmation": bool(confirmation),
                "pending_draft": self.drafts.get(conversation_id),
                **({"submission": submission} if submission else {}),
                **({"compaction": compacted} if compacted else {}),
            }
        )
        if compacted:
            mentions.insert(0, "Le début de la conversation a été résumé pour garder le contexte sous contrôle.")
        for mention in mentions:
            yield Event(type="mention", data={"content": mention})
        for chunk in _split(text):
            yield Event(type="text", data={"content": chunk})
        if confirmation_request:
            yield Event(type="confirmation_requested", data=confirmation_request)
        yield Event(type="end", data={"ok": True})


_DRAFT_LABELS = {"purchase_request": "demande d'achat", "invoice_approval": "approbation de facture"}
_WRITE_LABELS = {
    "prepare_purchase_request": "préparer une demande d'achat",
    "prepare_invoice_approval": "préparer l'approbation d'une facture",
}


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
        "prepare_purchase_request": "Préparation du brouillon de demande d'achat",
        "prepare_invoice_approval": "Préparation du brouillon d'approbation de la facture {invoice}",
    }
    try:
        return labels.get(name, name).format(**arguments)
    except (KeyError, IndexError):
        return name
