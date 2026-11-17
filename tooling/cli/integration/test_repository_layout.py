"""Repository layout: the inert-agent digest matches my-agent/, every workshop folder is complete."""

import re

import pytest

from workshop_tools.cli import ALL_WORKSHOPS, STEPS, workshop_tests_dir, workshop_dir

pytestmark = pytest.mark.shell


def test_bootstrap_is_the_one_recorded_for_check_inert():
    from workshop_tools.cli import bootstrap_changes

    assert bootstrap_changes() == [], "my-agent/ bootstrap changed: regenerate tooling/cli/inert_agent/bootstrap.sha256"


def test_every_workshop_folder_exists():
    missing = [i for i in ALL_WORKSHOPS if not workshop_tests_dir(i).is_dir()]
    assert missing == []
    assert all((workshop_dir(i) / "README.md").is_file() for i in ALL_WORKSHOPS)
    assert all((workshop_dir(i) / "state.yaml").is_file() for i in ALL_WORKSHOPS)


def test_steps_are_the_declared_ones():
    for workshop_id in ALL_WORKSHOPS:
        sources = "".join(f.read_text(encoding="utf-8") for f in workshop_tests_dir(workshop_id).glob("test_*.py"))
        marked = set(re.findall(r'etape\("([^"]+)"\)', sources))
        assert marked == set(STEPS.get(workshop_id, ())), f"workshop {workshop_id}: steps marked {sorted(marked)}"
