"""Private tests: `*_private.py` files and their cases, run only with `--private`.

They check the same success criteria as the public tests with other inputs (other customers,
references, phrasings, users, thresholds), to see whether an implementation generalises.
They are not given to students (see `export-ignore` in `.gitattributes`), nor are their cases
(`cases_private.yaml`, loaded by the private files only) and fixtures (`fixtures_private/`). `workshop check
<id> --private` adds them; `check-bootstrap` and `check-inert` always run them.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_addoption(parser):
    parser.addoption("--private", action="store_true", default=False, help="Also run the private tests (*_private.py)")


def pytest_configure(config):
    config.addinivalue_line("markers", "private: a private generalisation test (*_private.py)")


PRIVATE_CASES = "cases_private.yaml"
PRIVATE_FIXTURES = "fixtures_private"


def is_private_path(path: Path) -> bool:
    """A private test file, its cases or its fixtures."""
    return path.stem.endswith("_private") or path.name == PRIVATE_CASES or PRIVATE_FIXTURES in path.parts


def _is_private(item) -> bool:
    return is_private_path(item.path)


def pytest_ignore_collect(collection_path: Path, config):
    # Private cases are never collected as tests; without --private, private folders are not even walked.
    if collection_path.name == PRIVATE_CASES:
        return True
    if not config.getoption("--private") and collection_path.name == PRIVATE_FIXTURES:
        return True
    return None


def pytest_collection_modifyitems(config, items):
    for item in items:
        if _is_private(item):
            item.add_marker(pytest.mark.private)
    if config.getoption("--private"):
        return
    kept = [i for i in items if not _is_private(i)]
    deselected = [i for i in items if _is_private(i)]
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = kept
