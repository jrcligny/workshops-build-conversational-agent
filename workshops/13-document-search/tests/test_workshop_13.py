"""End-to-end tests of workshop 13. They must fail on the empty shell.

The checks (and the contract they read) are in `checks.py`; the cases in `cases.yaml`.
"""

import pytest

from workshop_tests.testing.cases import load_cases, load_checks

pytestmark = pytest.mark.workshop

checks = load_checks(__file__)
CASES = load_cases(__file__)


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
