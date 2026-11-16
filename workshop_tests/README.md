# Workshop test environment

This non-package uv project (`package = false`) owns test dependencies and
pytest configuration in `pyproject.toml`, with its own `uv.lock`, `.venv` and
`.python-version` (Python 3.13). It depends on the local `workshop-tools` project
in editable mode. Shared fixtures and clients live in `testing/`; the judge
and route-digest helpers live in `evaluation/`. These are not runtime services.

Run from the repository root, not from this directory:

```powershell
uv sync --project workshop_kit/bootstrap --locked --python 3.13
uv sync --project workshop_tests --locked --python 3.13
uv run --project workshop_tests pytest -c workshop_tests/pyproject.toml workshop_kit/tests
uv run --project workshop_kit/bootstrap workshop check 03
uv run --project workshop_kit/bootstrap workshop check 07 --non-regression
uv run --project workshop_kit/bootstrap workshop check-shell
```

Infrastructure tests must pass. Workshop acceptance tests stay next to their
guides and fail until implemented. The tooling CLI delegates checks here;
`-c` explicitly selects the test configuration and shared fixture plugin for
direct pytest runs. There is no root pytest configuration or `conftest.py`.
`python start.py` never installs these test dependencies.

To regenerate the official evaluation-route digest after an authorized team
change, run **from the repository root**:

```powershell
uv run --project workshop_tests python -m workshop_tests.evaluation.routes --write
```

The [route-set guide](../workshops/17-evaluation/routes/README.md) is itself
covered by the digest. Students and workshop 19 tooling must not change the
official routes or their checksum.

UI tests use the separate Chainlit project and its MCP 1 dependencies, never
this environment's MCP 2 dependencies:

```powershell
uv run --project workshop_kit/chat-ui --extra dev pytest --confcutdir workshop_kit/chat-ui workshop_kit/chat-ui/tests
```

See the [test inventory](../docs/test-inventory.md) and
[UI guide](../workshop_kit/chat-ui/README.md).