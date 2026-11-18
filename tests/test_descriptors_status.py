"""Gate A check (OD-12): descriptors.yaml must be approved law, not mock.
"""

from pathlib import Path

import yaml

PATH = Path(__file__).resolve().parent.parent / "docs" / "spec" / "descriptors.yaml"


def test_descriptors_are_approved():
    assert yaml.safe_load(PATH.read_text())["_meta"]["status"] == "approved"
