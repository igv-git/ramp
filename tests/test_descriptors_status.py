"""Gate A check (OD-12): descriptors.yaml must be approved law, not mock.

Non-strict xfail until the owner replaces the mock text; remove the marker at Gate A.
"""

from pathlib import Path

import pytest
import yaml

PATH = Path(__file__).resolve().parent.parent / "docs" / "spec" / "descriptors.yaml"


@pytest.mark.xfail(reason="mock descriptors until owner approves real law (OD-12); required at Gate A")
def test_descriptors_are_approved():
    assert yaml.safe_load(PATH.read_text())["_meta"]["status"] == "approved"
