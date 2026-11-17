"""Cases and checks shared by the public and the private tests of a workshop.

Each workshop's `tests/` folder holds:
- `checks.py`: one function per success criterion, parameterised by a case (no `test_` name);
- `cases.yaml`: the public cases, loaded by `test_workshop_XX.py`;
- `cases_private.yaml`: the private cases, loaded by `test_workshop_XX_private.py` only
  (not given to students, see `testkit.private`).

The test files stay thin: they load their cases, then call the same checks. Tests are collected
with `--import-mode=importlib`, so `checks.py` is loaded by path rather than imported.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

from testkit.private import PRIVATE_CASES

PUBLIC_CASES = "cases.yaml"
__all__ = ["PRIVATE_CASES", "PUBLIC_CASES", "load_cases", "load_checks"]


def load_cases(test_file: str, name: str = PUBLIC_CASES) -> dict[str, Any]:
    """The cases of the YAML file `name`, next to `test_file`."""
    path = Path(test_file).with_name(name)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: the cases file must map case names to cases")
    return data


def load_checks(test_file: str, name: str = "checks.py") -> ModuleType:
    """The module `name` next to `test_file`, loaded once whichever test file asks for it."""
    path = Path(test_file).with_name(name).resolve()
    key = "workshop_checks_" + hashlib.sha1(str(path).encode()).hexdigest()[:12]
    if key in sys.modules:
        return sys.modules[key]
    spec = importlib.util.spec_from_file_location(key, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module
