"""Contract the student's harness must implement. The shell does not implement it."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator, Protocol


@dataclass
class Message:
    role: str
    content: str


@dataclass
class TestUser:
    __test__ = False  # not a pytest test class

    id: str
    role: str
    organization: str
    app_token: str | None = None


@dataclass
class Event:
    # text, end, step, error, sources, mention, confirmation_requested, attachment, compaction, interruption
    type: str
    data: dict = field(default_factory=dict)


class HarnessContract(Protocol):
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
        """Runs one turn: assembles the system prompt and the history, calls the model,
        yields events and writes a trace.

        `history` is the transcript shown by the interface (user and final assistant texts), for
        information: the context sent to the model is `agent_sdk.context.context(conversation_id)`,
        which also keeps tool calls and their results.

        `attachments` is reserved for workshop 15.
        `interrupt_requested` (workshop 06) asks for a clean stop of the turn, with no new call.
        `confirmation` (workshop 10b) carries the user's confirmation gesture in the interface.
        `limits` (workshop 10d) may carry a duration and a budget.
        """
        ...


class HarnessNotImplemented(Exception):
    """Raised by the empty shell, with a message saying what is missing."""
