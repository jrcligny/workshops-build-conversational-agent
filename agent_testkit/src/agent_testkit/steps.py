"""Marker `etape("<name>")` and option `--etape <name>`: the steps of a workshop.

A workshop that covers several decisions of a chapter (05, 06, 07) splits its tests into steps
that share one scenario and one folder. `workshop check 07 --etape identite` passes
`--etape identite` to pytest: in the folders that contain tests of that step, the tests of the
other steps are deselected. Tests of other folders (the previous workshops of a non-regression
run) are left untouched.
"""

from __future__ import annotations

import pytest


def pytest_addoption(parser):
    parser.addoption("--etape", default=None, help="run only this step of the workshops that declare it")


def pytest_configure(config):
    config.addinivalue_line("markers", "etape(name): step of a workshop, selected by `--etape name`")


def _step(item) -> str | None:
    marker = item.get_closest_marker("etape")
    return str(marker.args[0]) if marker and marker.args else None


def pytest_collection_modifyitems(config, items):
    wanted = config.getoption("--etape")
    if not wanted:
        return
    folders = {item.path.parent for item in items if _step(item) == wanted}
    if not folders:
        raise pytest.UsageError(f"no test marked etape({wanted!r})")
    selected, deselected = [], []
    for item in items:
        (deselected if item.path.parent in folders and _step(item) != wanted else selected).append(item)
    if deselected:
        config.hook.pytest_deselected(items=deselected)
        items[:] = selected
