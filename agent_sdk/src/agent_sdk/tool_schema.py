"""Builds an OpenAI tool declaration from an annotated Python function.

What it gives you: `declare(function)` returns the dict to put in `generate(tools=[...])`:
name, description (the docstring's first paragraph) and a JSON schema of the parameters,
built from the type hints (`str`, `int`, `float`, `bool`, `list[...]`, `dict`, `Literal[...]`,
`X | None`) and the `Args:` section of the docstring. Parameters without a default are required.
The result is a plain dict: print it, read it, adjust it.

What stays yours: the tool names and parameters the workshops expect, descriptions that tell
the model when to use the tool, validating the arguments the model sends (workshop 04), running
the tool, and choosing which tools to offer at each call (workshops 13 and 14).
There is no registry and nothing runs automatically.

    def get_order(reference: str) -> dict:
        '''Reads one order by its reference.

        Args:
            reference: order reference, for example CMD-1042.
        '''

    declare(get_order)
    # {"type": "function", "function": {"name": "get_order", "description": "Reads one order...",
    #   "parameters": {"type": "object", "properties": {"reference": {"type": "string",
    #   "description": "order reference, for example CMD-1042."}}, "required": ["reference"]}}}

Only needs the standard library: usable from `harness.py` and from `mcp_server.py`.
"""

from __future__ import annotations

import inspect
import re
import types
import typing
from typing import Any, Callable, Literal

_SCALARS = {str: "string", int: "integer", float: "number", bool: "boolean", dict: "object"}


def declare(function: Callable, name: str | None = None, description: str | None = None) -> dict:
    doc = inspect.getdoc(function) or ""
    summary, arg_docs = _parse_docstring(doc)
    hints = typing.get_type_hints(function)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for param in inspect.signature(function).parameters.values():
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        schema, optional = _schema(hints.get(param.name, str))
        if param.name in arg_docs:
            schema["description"] = arg_docs[param.name]
        properties[param.name] = schema
        if param.default is inspect.Parameter.empty and not optional:
            required.append(param.name)
    return {
        "type": "function",
        "function": {
            "name": name or function.__name__,
            "description": description if description is not None else summary,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


def _schema(hint: Any) -> tuple[dict, bool]:
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)
    if origin in (typing.Union, types.UnionType):
        rest = [a for a in args if a is not type(None)]
        schema, _ = _schema(rest[0]) if len(rest) == 1 else ({}, False)
        return schema, type(None) in args
    if origin is Literal:
        values = list(args)
        kind = _SCALARS.get(type(values[0]), "string") if values else "string"
        return {"type": kind, "enum": values}, False
    if hint is list or origin is list:
        item = _schema(args[0])[0] if args else {}
        return {"type": "array", "items": item}, False
    if hint is dict or origin is dict:
        return {"type": "object"}, False
    return {"type": _SCALARS.get(hint, "string")}, False


def _parse_docstring(doc: str) -> tuple[str, dict[str, str]]:
    summary = doc.split("\n\n", 1)[0].replace("\n", " ").strip()
    arg_docs: dict[str, str] = {}
    match = re.search(r"^Args:[ \t]*\n((?:[ \t]+.*(?:\n|$))+)", doc, flags=re.MULTILINE)
    if not match:
        return summary, arg_docs
    lines = [line for line in match.group(1).splitlines() if line.strip()]
    item_indent = len(lines[0]) - len(lines[0].lstrip())
    current = None
    for line in lines:
        indent = len(line) - len(line.lstrip())
        item = re.match(r"\s*(\w+)\s*(?:\([^)]*\))?:\s*(.*)", line)
        if indent == item_indent and item:
            current = item.group(1)
            arg_docs[current] = item.group(2).strip()
        elif current:
            arg_docs[current] += " " + line.strip()
    return summary, arg_docs