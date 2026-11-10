import pytest


@pytest.fixture
def tmp_home(tmp_path, monkeypatch):
    """A throwaway RAMP_HOME for tests."""
    home = tmp_path / "ramp_home"
    home.mkdir()
    monkeypatch.setenv("RAMP_HOME", str(home))
    return home
