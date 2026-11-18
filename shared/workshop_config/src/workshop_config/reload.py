"""Hot reload of my-agent/: one signature of its Python files, shared by the interface and the MCP runner.

Polling (a `stat` of each file) rather than file system events: it behaves the same on Windows, macOS,
Linux and WSL, including on Windows drives mounted in WSL, where inotify sees no change.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import os
import sys
import traceback
from collections.abc import Iterable
from pathlib import Path

Signature = tuple[tuple[str, int, int], ...]


def source_signature(folder: Path) -> Signature:
    """(relative path, mtime in ns, size) of each `.py` file of the folder, virtual environments excluded."""
    entries = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith(".") and d != "__pycache__")
        for name in files:
            if name.endswith(".py"):
                path = Path(root) / name
                try:
                    stat = path.stat()
                except OSError:
                    continue
                entries.append((path.relative_to(folder).as_posix(), stat.st_mtime_ns, stat.st_size))
    return tuple(sorted(entries))


def digest(signature: Signature) -> str:
    return hashlib.sha256(repr(signature).encode("utf-8")).hexdigest()[:16]


def changed_files(before: Signature, after: Signature) -> list[str]:
    old, new = {e[0]: e[1:] for e in before}, {e[0]: e[1:] for e in after}
    return sorted(name for name in old.keys() | new.keys() if old.get(name) != new.get(name))


def _inside(path: str | None, folder: Path) -> bool:
    """A file of the student's code: in the folder, outside its virtual environment and hidden folders."""
    if not path:
        return False
    try:
        parts = Path(path).resolve().relative_to(folder).parts
    except (OSError, ValueError):
        return False
    return not any(part.startswith(".") or part == "__pycache__" for part in parts[:-1])


def purge_modules(folder: Path, changed: Iterable[str] = ()) -> list[str]:
    """Forgets every loaded module whose file is in the folder, so the next import reads the files again.

    The bytecode of the changed files is removed too: Python only compares the modification second
    and the size, so a quick edit that keeps the size could otherwise run the old code.
    """
    folder = folder.resolve()
    for name in changed:
        try:
            Path(importlib.util.cache_from_source(str(folder / name))).unlink(missing_ok=True)
        except (OSError, ValueError, NotImplementedError):
            pass
    names = [name for name, module in list(sys.modules.items()) if _inside(getattr(module, "__file__", None), folder)]
    for name in names:
        sys.modules.pop(name, None)
    importlib.invalidate_caches()
    return sorted(names)


def describe_error(exc: BaseException, folder: Path) -> str:
    """One line for the student: the file and line of my-agent/ at fault, then the error."""
    folder = folder.resolve()
    where = None
    if isinstance(exc, SyntaxError) and _inside(exc.filename, folder):
        where = (exc.filename, exc.lineno)
    else:
        for frame in reversed(traceback.extract_tb(exc.__traceback__)):
            if _inside(frame.filename, folder):
                where = (frame.filename, frame.lineno)
                break
    message = (exc.msg if isinstance(exc, SyntaxError) else str(exc)).rstrip(". ")
    text = f"{type(exc).__name__}: {message}" if message else type(exc).__name__
    if where is None:
        return text
    relative = Path(where[0]).resolve().relative_to(folder.parent).as_posix()
    return f"{relative}, line {where[1]}: {text}"
