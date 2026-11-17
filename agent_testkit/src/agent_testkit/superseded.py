"""Marker `superseded_by("<id>")`: a test of an earlier workshop that a later workshop deliberately reverses.

For example, workshop 03 requires an agent without tools; workshop 04 gives it one. When the
target workshop (environment variable `WORKSHOP_TARGET`, set by `workshop check`) is at or past
`<id>`, the test is skipped with an explicit reason instead of failing the non-regression run.
Without a target (check-bootstrap, check-inert, plain pytest), the test runs.
"""

from __future__ import annotations

import os

import pytest


def _key(workshop_id: str) -> tuple[int, str]:
    digits = "".join(ch for ch in workshop_id if ch.isdigit())
    return int(digits or 0), workshop_id[len(digits):]


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "superseded_by(workshop_id): skipped once the target workshop reaches workshop_id"
    )


def pytest_collection_modifyitems(config, items):
    target = os.environ.get("WORKSHOP_TARGET", "").strip()
    if not target:
        return
    for item in items:
        marker = item.get_closest_marker("superseded_by")
        if marker and marker.args and _key(target) >= _key(str(marker.args[0])):
            item.add_marker(pytest.mark.skip(reason=f"superseded by workshop {marker.args[0]} (target {target})"))
