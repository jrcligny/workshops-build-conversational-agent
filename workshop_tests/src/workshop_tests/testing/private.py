"""Private tests: `*_private.py` files, run only with `--private`.

They check the same success criteria as the public tests with other inputs (other customers,
references, phrasings, users, thresholds), to see whether an implementation generalises.
They are not given to students (see `export-ignore` in `.gitattributes`). `workshop check
<id> --private` adds them; `check-bootstrap` and `check-inert` always run them.
"""

from __future__ import annotations

import pytest


def pytest_addoption(parser):
    parser.addoption("--private", action="store_true", default=False, help="Also run the private tests (*_private.py)")


def pytest_configure(config):
    config.addinivalue_line("markers", "private: a private generalisation test (*_private.py)")


def _is_private(item) -> bool:
    return item.path.stem.endswith("_private")


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
