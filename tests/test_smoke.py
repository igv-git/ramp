import importlib

import pytest

MODULES = ["cli", "loop", "agents", "providers", "gate", "runner", "review", "plan", "matrix", "store", "lint"]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(f"ramp.{name}")
