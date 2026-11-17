"""Integrity of the evaluation routes (workshop 15), checked by workshops 15 and 17 and by the kit tests.

Loaded by path (`agent_testkit.cases.load_checks`), like `checks.py`; it imports nothing from the kit.

The digest covers every file of the routes folder except the checksum file itself:
relative POSIX path, then content with line endings normalised to LF, so the value
is the same on Windows (CRLF checkout) and on Linux.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

ROUTES_DIR = Path(__file__).resolve().parents[1] / "routes"
CHECKSUM_FILE = "routes.sha256"


def routes_digest(folder: Path = ROUTES_DIR) -> str:
    h = hashlib.sha256()
    files = [p for p in folder.rglob("*") if p.is_file() and p.name != CHECKSUM_FILE]
    for path in sorted(files, key=lambda p: p.relative_to(folder).as_posix()):
        h.update(path.relative_to(folder).as_posix().encode())
        h.update(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
    return h.hexdigest()


def expected_digest(folder: Path = ROUTES_DIR) -> str:
    return (folder / CHECKSUM_FILE).read_text(encoding="utf-8").strip()


def write_digest(folder: Path = ROUTES_DIR) -> str:
    digest = routes_digest(folder)
    (folder / CHECKSUM_FILE).write_text(digest + "\n", encoding="utf-8", newline="\n")
    return digest


if __name__ == "__main__":
    import sys

    # `--write` regenerates routes.sha256 (team only); otherwise the digest is printed.
    print(write_digest() if "--write" in sys.argv[1:] else routes_digest())
