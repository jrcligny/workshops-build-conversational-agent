"""Workshop CLI: serve the stack, show guides, and run workshop checks."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKSHOPS_DIR = REPO_ROOT / "workshops"
SHELL_REPORT = REPO_ROOT / ".pytest_shell.xml"

# Workshop id -> folder under workshops/. Chapter 10 is split into 10a to 10d.
WORKSHOPS = {
    "03": "03-system-prompt",
    "04": "04-first-tool",
    "05": "05-read-tools",
    "06": "06-agent-loop",
    "07": "07-context-compaction",
    "08": "08-working-memory",
    "09": "09-mcp",
    "10a": "10a-identity",
    "10b": "10b-writes",
    "10c": "10c-groupings",
    "10d": "10d-sandboxing",
    "11": "11-architecture",
    "12": "12-long-term-memory",
    "13": "13-document-search",
    "14": "14-skills",
    "15": "15-read-without-obeying",
    "16": "16-controls",
    "17": "17-evaluation",
    "18": "18-failures",
    "19": "19-specification",
}
WORKSHOP_IDS = list(WORKSHOPS)


def _check_id(workshop_id: str) -> None:
    if workshop_id not in WORKSHOPS:
        raise SystemExit(f"unknown workshop: {workshop_id} (expected one of {', '.join(WORKSHOP_IDS)})")


def up_to(workshop_id: str) -> list[str]:
    _check_id(workshop_id)
    return WORKSHOP_IDS[: WORKSHOP_IDS.index(workshop_id) + 1]


def workshop_dir(workshop_id: str) -> Path:
    return WORKSHOPS_DIR / WORKSHOPS[workshop_id]


def workshop_tests_dir(workshop_id: str) -> Path:
    return workshop_dir(workshop_id) / "tests"


def _pytest(folders: list[Path], extra: list[str] | None = None) -> int:
    args = [sys.executable, "-m", "pytest", *[str(d) for d in folders], *(extra or [])]
    return subprocess.call(args, cwd=REPO_ROOT)


def cmd_check(workshop_id: str, non_regression: bool) -> int:
    _check_id(workshop_id)
    ids = up_to(workshop_id) if non_regression else [workshop_id]
    missing = [i for i in ids if not workshop_tests_dir(i).is_dir()]
    if missing:
        print(f"missing test folders: {', '.join(missing)}", file=sys.stderr)
        return 2
    print(f"Checking workshops: {', '.join(ids)}")
    return _pytest([workshop_tests_dir(i) for i in ids], ["-m", "workshop"])


def cmd_check_shell() -> int:
    """Succeeds (exit code 0) when every workshop test fails or errors, and none passes."""
    folders = [workshop_tests_dir(i) for i in WORKSHOP_IDS if workshop_tests_dir(i).is_dir()]
    if not folders:
        print("no workshops/*/tests folder found", file=sys.stderr)
        return 2
    proc = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            *[str(d) for d in folders],
            "-m", "workshop",
            "-q",
            "--tb=no",
            "--color=no",
            f"--junitxml={SHELL_REPORT}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return _interpret_shell_run((proc.stdout or "") + (proc.stderr or ""), SHELL_REPORT)


def _interpret_shell_run(output: str, report: Path | None = None) -> int:
    """0 when everything failed as intended, 1 otherwise, 2 when nothing was collected."""
    passed = failed = errors = collected = skipped = 0
    if report and report.exists():
        root = ET.parse(report).getroot()
        # pytest may emit a <testsuites> wrapper or a bare <testsuite>.
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        for suite in suites:
            collected += int(suite.attrib.get("tests") or 0)
            failed += int(suite.attrib.get("failures") or 0)
            errors += int(suite.attrib.get("errors") or 0)
            skipped += int(suite.attrib.get("skipped") or 0)
        passed = max(collected - failed - errors - skipped, 0)
    if collected == 0:
        for pattern, name in ((r"(\d+) passed", "passed"), (r"(\d+) failed", "failed"), (r"(\d+) error", "errors"), (r"collected (\d+) item", "collected")):
            m = re.search(pattern, output)
            if m:
                value = int(m.group(1))
                if name == "passed":
                    passed = value
                elif name == "failed":
                    failed = value
                elif name == "errors":
                    errors = value
                else:
                    collected = value
    if collected == 0 and (failed + passed + errors) == 0:
        print("no workshop test collected", file=sys.stderr)
        return 2
    print(
        f"Empty shell: {passed} passed, {failed} failed, {errors} error(s) "
        f"(collected: {collected or failed + passed + errors})."
    )
    if passed > 0:
        print(
            "ERROR: at least one workshop test passes on the empty shell. "
            "All of them must fail until the workshop is done.",
            file=sys.stderr,
        )
        return 1
    if failed + errors == 0:
        print("ERROR: no workshop test failed.", file=sys.stderr)
        return 1
    print("Expected behaviour: every workshop test fails on the empty shell.")
    return 0


def cmd_start(workshop_id: str) -> int:
    _check_id(workshop_id)
    guide = workshop_dir(workshop_id) / "README.md"
    print(f"Workshop {workshop_id}. No solution is copied: you work in my-agent/.")
    if guide.exists():
        print(f"Guide: {guide.relative_to(REPO_ROOT).as_posix()}")
    print("Start the applications if you want to explore by hand (see docs/installation.md), then:")
    print(f"  uv run workshop check {workshop_id}")
    if not (REPO_ROOT / "my-agent" / "harness.py").exists():
        print("Warning: my-agent/harness.py is missing.", file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="workshop", description="Tools for the companion workshops.")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="Run the tests of one workshop")
    check.add_argument("workshop_id")
    check.add_argument("--non-regression", action="store_true", help="Also run the previous workshops")

    sub.add_parser("check-shell", help="Check that every workshop test fails on the empty shell")

    start = sub.add_parser("start", help="Show the workshop guide, without copying any agent code")
    start.add_argument("workshop_id")

    serve = sub.add_parser("serve", help="Start all services, including the Chainlit chat UI")
    serve.add_argument("--port-offset", type=int, default=0, help="Shift all six default ports")
    serve.add_argument("--reset-data", action="store_true", help="Reset the business dataset and document index")

    args = parser.parse_args(argv)
    if args.command == "check":
        return cmd_check(args.workshop_id, args.non_regression)
    if args.command == "check-shell":
        return cmd_check_shell()
    if args.command == "start":
        return cmd_start(args.workshop_id)
    if args.command == "serve":
        from workshop_kit.devstack import serve as serve_stack

        return serve_stack(args.port_offset, args.reset_data)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
