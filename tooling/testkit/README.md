# Workshop test environment

Three projects under `tooling/`, with dependencies in one direction only:
`cli` → `testkit` → `evaluation`.

- `tooling/testkit/` (package `testkit`): what `workshops/*/tests` import. Pytest
  plugins (`fixtures`, `superseded`, `private`), `ChatClient`, `cases`
  (`load_cases`, `load_checks`), `conversation` (injected conversations),
  `turns`, `servers` and `probes`. Its own tests are in `tests/`.
- `tooling/evaluation/` (package `evaluation`): the judge (structural layer,
  then meaning layer), tested in `tests/test_judge.py`. The k-out-of-n
  repetition (`testkit.turns.apply_rubric_repeatedly`) is tested in testkit.
- `tooling/cli/`: runs the tests. Its `tests` dependency group (never installed
  by `python start.py`) holds testkit, evaluation and the services; its
  `pyproject.toml` holds the pytest configuration. It also holds what checks the
  kit itself: `integration/` (cross-component tests), `inert_agent/` (overlay of
  `check-inert`; its `route-report.*` are facade deliverables, not generated
  files) and `bootstrap_passes.txt` (`check-bootstrap`).

The evaluation routes of workshop 17 (`routes.py`, `route_runner.py`) live in
`workshops/17-evaluation/tests/`, loaded by path like `checks.py`.

Run from the repository root:

```powershell
uv sync --project tooling/cli --group tests --locked --python 3.13
uv run --project tooling/cli --group tests pytest -c tooling/cli/pyproject.toml agent_sdk business gateway tooling
uv run --project tooling/cli workshop check 03
uv run --project tooling/cli workshop check 07 --non-regression
uv run --project tooling/cli workshop check-bootstrap
```

Infrastructure tests must pass. Workshop acceptance tests stay next to their
guides and fail until implemented. `-c` explicitly selects the test
configuration and the shared plugins for direct pytest runs. There is no root
pytest configuration or `conftest.py`.

To regenerate the official evaluation-route digest after an authorized team
change, run **from the repository root**:

```powershell
uv run --project tooling/cli --group tests python workshops/17-evaluation/tests/routes.py --write
```

The [route-set guide](../../workshops/17-evaluation/routes/README.md) is itself
covered by the digest. Students and workshop 19 tooling must not change the
official routes or their checksum.

UI tests use the separate Chainlit project and its MCP 1 dependencies, never
this environment's MCP 2 dependencies:

```powershell
uv run --project clients/chat_ui --extra dev pytest --confcutdir clients/chat_ui clients/chat_ui/tests
```

See the [test inventory](../../docs/test-inventory.md) and
[UI guide](../../clients/chat_ui/README.md).
