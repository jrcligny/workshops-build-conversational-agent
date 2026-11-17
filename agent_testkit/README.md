# Workshop test environment

`agent_testkit/` is what tests the agent, as `agent_sdk/` is what the agent imports.
Students never import it. Dependencies go in one direction only:
`tooling/cli` → `agent_testkit` → `agent_testkit.evaluation`.

- `agent_testkit/` (package `agent_testkit`): what `workshops/*/tests` import. Pytest
  plugins (`fixtures`, `superseded`, `private`), `ChatClient`, `cases`
  (`load_cases`, `load_checks`), `conversation` (injected conversations),
  `expect` (business assertions), `turns`, `servers` and `probes`. Its tests are in `tests/`.
- `agent_testkit.evaluation`: the judge (structural layer, then meaning layer),
  tested in `tests/test_judge.py`. It imports nothing else from `agent_testkit`;
  the k-out-of-n repetition (`agent_testkit.turns.apply_rubric_repeatedly`) is
  tested in `tests/test_turns.py`.
- `tooling/cli/`: runs the tests. Its `tests` dependency group (never installed
  by `python start.py`) holds `agent_testkit` and the services; its
  `pyproject.toml` holds the pytest configuration. It also holds what checks the
  kit itself: `integration/` (cross-component tests), `inert_agent/` (overlay of
  `check-inert`; its `route-report.*` are facade deliverables, not generated
  files) and `bootstrap_passes.txt` (`check-bootstrap`).

The evaluation routes of workshop 15 (`routes.py`, `route_runner.py`) live in
`workshops/15-evaluation/tests/`, loaded by path like `checks.py`.

Run from the repository root:

```powershell
uv sync --project tooling/cli --group tests --locked --python 3.13
uv run --project tooling/cli --group tests pytest -c tooling/cli/pyproject.toml agent_sdk agent_testkit business gateway tooling
uv run --project tooling/cli workshop check 03
uv run --project tooling/cli workshop check 09 --non-regression
uv run --project tooling/cli workshop check-bootstrap
```

Infrastructure tests must pass. Workshop acceptance tests stay next to their
guides and fail until implemented. `-c` explicitly selects the test
configuration and the shared plugins for direct pytest runs. There is no root
pytest configuration or `conftest.py`.

To regenerate the official evaluation-route digest after an authorized team
change, run **from the repository root**:

```powershell
uv run --project tooling/cli --group tests python workshops/15-evaluation/tests/routes.py --write
```

The [route-set guide](../workshops/15-evaluation/routes/README.md) is itself
covered by the digest. Students and workshop 17 tooling must not change the
official routes or their checksum.

UI tests use the separate Chainlit project and its MCP 1 dependencies, never
this environment's MCP 2 dependencies:

```powershell
uv run --project clients/chat_ui --extra dev pytest --confcutdir clients/chat_ui clients/chat_ui/tests
```

See the [test inventory](../docs/test-inventory.md) and
[UI guide](../clients/chat_ui/README.md).
