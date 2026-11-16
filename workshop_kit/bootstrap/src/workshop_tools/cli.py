"""Workshop CLI: serve the stack, show guides, and run workshop checks."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
TEST_PROJECT = REPO_ROOT / "workshop_tests"
WORKSHOPS_DIR = REPO_ROOT / "workshops"
SHELL_REPORT = REPO_ROOT / ".pytest_shell.xml"

# Workshop id -> folder under workshops/. Chapter 10 is split into 10a to 10d.
WORKSHOPS = {
    "03": "03-system-prompt",
    "04": "04-first-tool",
    "05": "05-read-tools",
    "06": "06-agent-loop",
    "07": "07-progressive-disclosure",
    "08": "08-context-compaction",
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


def _pytest_command() -> list[str]:
    uv = shutil.which("uv")
    if not uv:
        raise SystemExit("uv is required to run the test project's own environment.")
    return [
        uv, "run", "--project", str(TEST_PROJECT), "--locked", "python", "-m", "pytest",
        "-c", str(TEST_PROJECT / "pyproject.toml"), "--rootdir", str(REPO_ROOT),
    ]


def _test_env() -> dict[str, str]:
    return {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}


def _pytest(folders: list[Path], extra: list[str] | None = None, env_overrides: dict[str, str] | None = None) -> int:
    args = [*_pytest_command(), *[str(d) for d in folders], *(extra or [])]
    return subprocess.call(args, cwd=REPO_ROOT, env={**_test_env(), **(env_overrides or {})})


def cmd_check(workshop_id: str, non_regression: bool) -> int:
    _check_id(workshop_id)
    ids = up_to(workshop_id) if non_regression else [workshop_id]
    missing = [i for i in ids if not workshop_tests_dir(i).is_dir()]
    if missing:
        print(f"missing test folders: {', '.join(missing)}", file=sys.stderr)
        return 2
    print(f"Checking workshops: {', '.join(ids)}")
    # Tests marked superseded_by(<id>) are skipped once the target workshop reaches <id>.
    return _pytest([workshop_tests_dir(i) for i in ids], ["-m", "workshop"], {"WORKSHOP_TARGET": workshop_id})


def _run_expect_all_fail(label: str, env_overrides: dict[str, str] | None = None) -> int:
    """Runs every workshop test and succeeds (exit code 0) when each one fails or errors."""
    folders = [workshop_tests_dir(i) for i in WORKSHOP_IDS if workshop_tests_dir(i).is_dir()]
    if not folders:
        print("no workshops/*/tests folder found", file=sys.stderr)
        return 2
    env = _test_env()
    env.update(env_overrides or {})
    proc = subprocess.run(
        [
            *_pytest_command(),
            *[str(d) for d in folders],
            "-m", "workshop",
            "-q",
            "--tb=no",
            "--color=no",
            "-rA",
            f"--junitxml={SHELL_REPORT}",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr, file=sys.stderr)
    return _interpret_shell_run((proc.stdout or "") + (proc.stderr or ""), SHELL_REPORT, label)


def cmd_check_shell() -> int:
    """Succeeds (exit code 0) when every workshop test fails or errors on the empty shell."""
    return _run_expect_all_fail("Empty shell")


def cmd_check_inert() -> int:
    """Succeeds when every workshop test fails against the inert agent of workshop_tests/inert_agent.

    The inert agent answers a cautious French sentence, calls neither the model nor a tool,
    and ships facade deliverables; a test it passes is too lenient.
    """
    inert = TEST_PROJECT / "inert_agent"
    return _run_expect_all_fail(
        "Inert agent",
        {
            "MY_AGENT_DIR": str(inert),
            "SANDBOX_POLICY_FILE": str(inert / "sandbox" / "policy.yaml"),
            "SKILLS_DIR": str(inert / "skills"),
            "ATTACHMENTS_DIR": str(inert / "attachments"),
        },
    )


def _passed_tests(report: Path) -> list[str]:
    root = ET.parse(report).getroot()
    names = []
    for case in root.iter("testcase"):
        if not any(child.tag in ("failure", "error", "skipped") for child in case):
            names.append(f"{case.attrib.get('classname', '')}::{case.attrib.get('name', '')}")
    return names


def _interpret_shell_run(output: str, report: Path | None = None, label: str = "Empty shell") -> int:
    """0 when everything failed as intended, 1 otherwise, 2 when nothing was collected."""
    passed = failed = errors = collected = skipped = 0
    passed_names: list[str] = []
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
        passed_names = _passed_tests(report)
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
        f"{label}: {passed} passed, {failed} failed, {errors} error(s) "
        f"(collected: {collected or failed + passed + errors})."
    )
    if passed > 0:
        print(
            f"ERROR: at least one workshop test passes ({label.lower()}). "
            "All of them must fail until the workshop is done.",
            file=sys.stderr,
        )
        for name in passed_names:
            print(f"  passes: {name}", file=sys.stderr)
        return 1
    if failed + errors == 0:
        print("ERROR: no workshop test failed.", file=sys.stderr)
        return 1
    print(f"Expected behaviour: every workshop test fails ({label.lower()}).")
    return 0

def cmd_start(workshop_id: str) -> int:
    _check_id(workshop_id)
    guide = workshop_dir(workshop_id) / "README.md"
    print(f"Workshop {workshop_id}. No solution is copied: you work in my-agent/.")
    if guide.exists():
        print(f"Guide: {guide.relative_to(REPO_ROOT).as_posix()}")
    print("Start the applications if you want to explore by hand (see docs/installation.md), then:")
    print(f"  uv run --project workshop_kit/bootstrap workshop check {workshop_id}")
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
    sub.add_parser("check-inert", help="Check that every workshop test fails against the inert agent")

    start = sub.add_parser("start", help="Show the workshop guide, without copying any agent code")
    start.add_argument("workshop_id")

    serve = sub.add_parser("serve", help="Start all services, including the Chainlit chat UI")
    serve.add_argument("--port-offset", type=int, default=0, help="Shift all six default ports")
    serve.add_argument("--reset-data", action="store_true", help="Reset the business dataset and document index")
    serve.add_argument("--check", action="store_true", help="Validate startup of all isolated services, then stop")

    args = parser.parse_args(argv)
    if args.command == "check":
        return cmd_check(args.workshop_id, args.non_regression)
    if args.command == "check-shell":
        return cmd_check_shell()
    if args.command == "check-inert":
        return cmd_check_inert()
    if args.command == "start":
        return cmd_start(args.workshop_id)
    if args.command == "serve":
        from workshop_tools.devstack import serve as serve_stack

        return serve_stack(args.port_offset, args.reset_data, check_only=args.check)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
