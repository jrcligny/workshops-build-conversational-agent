"""Shared cases and checks of the workshop tests (public and private)."""

from pathlib import Path

from agent_testkit.cases import PRIVATE_CASES, load_cases, load_checks
from agent_testkit.private import is_private_path


def test_cases_and_checks_are_loaded_next_to_the_test_file(tmp_path):
    (tmp_path / "cases.yaml").write_text("lookup:\n  reference: CMD-1042\n", encoding="utf-8")
    (tmp_path / PRIVATE_CASES).write_text("lookup:\n  reference: CMD-2010\n", encoding="utf-8")
    (tmp_path / "checks.py").write_text("calls = []\ndef lookup(case):\n    calls.append(case['reference'])\n", encoding="utf-8")
    test_file = str(tmp_path / "test_workshop_99.py")

    checks = load_checks(test_file)
    checks.lookup(load_cases(test_file)["lookup"])
    load_checks(str(tmp_path / "test_workshop_99_private.py")).lookup(load_cases(test_file, PRIVATE_CASES)["lookup"])

    assert checks.calls == ["CMD-1042", "CMD-2010"], "public and private tests share one checks module"


def test_private_material_is_recognised():
    assert is_private_path(Path("workshops/04-first-tool/tests/test_workshop_04_private.py"))
    assert is_private_path(Path("workshops/04-first-tool/tests/cases_private.yaml"))
    assert is_private_path(Path("workshops/15-read-without-obeying/tests/fixtures_private/note.txt"))
    assert not is_private_path(Path("workshops/04-first-tool/tests/cases.yaml"))
    assert not is_private_path(Path("workshops/04-first-tool/tests/checks.py"))
