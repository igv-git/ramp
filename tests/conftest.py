import shutil
from pathlib import Path

import pytest

from ramp import config

SPEC = Path(__file__).resolve().parent.parent / "docs" / "spec"


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    """A throwaway RAMP_HOME for tests."""
    home = tmp_path / "ramp_home"
    home.mkdir()
    monkeypatch.setenv("RAMP_HOME", str(home))
    return home


def good_config_text() -> str:
    return (config.default_toml().replace("REPLACE_ME_DIFFERENT", "rev-model")
            .replace("REPLACE_ME_CHEAP", "cheap-model").replace('model = "REPLACE_ME"', 'model = "strong-model"'))


@pytest.fixture
def law_home(tmp_home):
    """tmp_home with a valid config and the repo's approved descriptors/claims copied in."""
    (tmp_home / "config.toml").write_text(good_config_text())
    shutil.copy(SPEC / "descriptors.yaml", tmp_home / "descriptors.yaml")
    shutil.copy(SPEC / "claims.yaml", tmp_home / "claims.yaml")
    return tmp_home
