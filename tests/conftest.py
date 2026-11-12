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


@pytest.fixture
def curriculum(law_home):
    """A real 2-slice curriculum built through init_flow with scripted agents; yields (ctx, llm)."""
    import builders as b

    from ramp.cli import wiring
    from ramp.loop import init_flow
    from ramp.providers.port import FakeLLM

    llm = FakeLLM({"planner": [b.eligible(), b.outline(2, 30)], "writer": [b.slice_for(1), b.slice_for(2)]})
    ctx = wiring.make_context(law_home, llm=llm)
    init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=2, hours_per_day=1.0, days=1,
                       deadline=None, goals=[])
    llm.calls.clear()
    yield ctx, llm
    ctx.store.close()


def write_solution(home, text=None, slice_no="01"):
    import builders as b

    p = home / "slices" / slice_no / "workspace" / "src" / "wc" / "__init__.py"
    p.write_text(text if text is not None else b.SOLUTION)
    return p
