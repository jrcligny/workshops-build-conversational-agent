"""Runtime probes: what the student's code actually opens or connects to during a turn.

The services run in the test process, so a Python audit hook sees every `open`,
`socket.getaddrinfo` and `socket.connect` they trigger. Only events whose call stack goes
through a file of the student's folder (`my-agent/`) are recorded.
"""

from __future__ import annotations

import sys
import threading
from contextlib import contextmanager
from pathlib import Path

from workshop_config import repo_path, settings

_lock = threading.Lock()
_active: list[dict] = []
_installed = False
_EVENTS = {"open", "socket.getaddrinfo", "socket.connect"}


def _student_frame(root: str) -> str | None:
    frame = sys._getframe(2)
    while frame is not None:
        name = frame.f_code.co_filename
        if name.startswith(root):
            return name
        frame = frame.f_back
    return None


def _hook(event, args):
    if event not in _EVENTS or not _active:
        return
    for probe in list(_active):
        origin = _student_frame(probe["root"])
        if origin:
            target = args[1] if event == "socket.connect" and len(args) > 1 else (args[0] if args else None)
            probe["events"].append({"event": event, "target": target, "origin": origin})


@contextmanager
def student_activity():
    """Collects the file and network activity of the code in `my-agent/` during the block."""
    global _installed
    with _lock:
        if not _installed:
            sys.addaudithook(_hook)
            _installed = True
    probe = {"root": str(repo_path(settings.my_agent_dir).resolve()), "events": []}
    _active.append(probe)
    try:
        yield probe["events"]
    finally:
        _active.remove(probe)


def opened_files(events: list[dict], allowed: list[Path]) -> list[str]:
    """Files opened by the student's code outside the allowed folders."""
    roots = [str(p.resolve()) for p in allowed]
    found = []
    for e in events:
        if e["event"] != "open" or not isinstance(e["target"], (str, Path)):
            continue
        target = str(Path(e["target"]).resolve())
        if not any(target.startswith(r) for r in roots):
            found.append(target)
    return found


def contacted_hosts(events: list[dict]) -> set[str]:
    hosts = set()
    for e in events:
        if e["event"] == "socket.getaddrinfo" and e["target"]:
            hosts.add(str(e["target"]))
        elif e["event"] == "socket.connect" and isinstance(e["target"], tuple) and e["target"]:
            hosts.add(str(e["target"][0]))
    return hosts
