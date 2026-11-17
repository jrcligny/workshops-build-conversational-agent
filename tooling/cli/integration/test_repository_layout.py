"""Repository layout: the inert-agent digest matches my-agent/, every workshop folder is complete."""

import pytest

from workshop_tools.cli import WORKSHOP_IDS, workshop_tests_dir, workshop_dir

pytestmark = pytest.mark.shell


def test_bootstrap_is_the_one_recorded_for_check_inert():
    from workshop_tools.cli import bootstrap_changes

    assert bootstrap_changes() == [], "my-agent/ bootstrap changed: regenerate tooling/cli/inert_agent/bootstrap.sha256"


def test_every_workshop_folder_exists():
    missing = [i for i in WORKSHOP_IDS if not workshop_tests_dir(i).is_dir()]
    assert missing == []
    assert all((workshop_dir(i) / "README.md").is_file() for i in WORKSHOP_IDS)
    assert all((workshop_dir(i) / "state.yaml").is_file() for i in WORKSHOP_IDS)
