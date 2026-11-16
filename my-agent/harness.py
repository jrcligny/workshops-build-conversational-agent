"""Empty shell.

This file is the entry point of your agent. The repository provides neither
the conversational loop nor the system prompt: that is the work of workshop 03.

The contract to implement: the Harness class exposes a turn(...) method that
receives the conversation id, the user's message, the test user and the
history, then yields events (text, then end) and writes a trace. Use the
kit's model client (wired to the proxy) and the trace helpers.

Your agent converses in French: the tests send French user turns and expect
French answers (code, comments and identifiers stay English).
"""

from __future__ import annotations

from collections.abc import Iterator

from workshop_kit.shell.harness_contract import Event, Message, TestUser


class Harness:
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
        raise NotImplementedError(
            "Your turn: implement the system prompt and the conversational loop "
            "(workshop 03). The shell provides neither."
        )
