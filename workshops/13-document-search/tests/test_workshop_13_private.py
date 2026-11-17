"""Private tests of workshop 13 (not given to students): same checks (`checks.py`), other cases
(`cases_private.yaml`): another document (claim deadline 1.3, whose version 1.2 is retired),
another question without a documentary answer, another role-restricted document (purchasing
workflow, buyer only) and another order next to the procedure.
"""

import pytest

from testkit.cases import PRIVATE_CASES, load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__, PRIVATE_CASES)


def test_document_search_and_sources(chat_client):
    checks.document_search_and_sources(chat_client, CASES["document_search_and_sources"])


def test_empty_result_declared(chat_client):
    checks.empty_result_declared(chat_client, CASES["empty_result_declared"])


def test_permission_filtering(chat_client, services):
    checks.permission_filtering(chat_client, services, CASES["permission_filtering"])


def test_retired_version_absent(chat_client):
    checks.retired_version_absent(chat_client, CASES["retired_version_absent"])


def test_documentation_distinguished_from_data(chat_client):
    checks.documentation_distinguished_from_data(chat_client, CASES["documentation_distinguished_from_data"])
