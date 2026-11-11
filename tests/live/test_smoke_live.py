"""Opt-in live smoke: real provider, real models. Skipped unless a key and a finished config are present.

Run:  OPENROUTER_API_KEY=... uv run pytest tests/live -m live -s
Config: RAMP_LIVE_CONFIG (path to a config.toml) or ~/.ramp/config.toml, with no REPLACE_ME models.
"""

import os
import shutil
from pathlib import Path

import pytest

from ramp.cli import wiring
from ramp.config import ConfigError, load_config
from ramp.loop import init_flow

pytestmark = pytest.mark.live
SPEC = Path(__file__).resolve().parents[2] / "docs" / "spec"
CONFIG = Path(os.environ.get("RAMP_LIVE_CONFIG", Path.home() / ".ramp" / "config.toml"))


def _ready() -> str | None:
    if not os.environ.get("OPENROUTER_API_KEY"):
        return "OPENROUTER_API_KEY not set"
    if not CONFIG.exists():
        return f"{CONFIG} not found"
    try:
        cfg = load_config(CONFIG)
        for role in ("planner", "writer", "reviewer", "grader"):
            cfg.require_model(role)
    except ConfigError as e:
        return str(e)
    return None


@pytest.mark.skipif(_ready() is not None, reason=_ready() or "")
def test_init_python_with_real_provider(tmp_home):
    shutil.copy(CONFIG, tmp_home / "config.toml")
    shutil.copy(SPEC / "descriptors.yaml", tmp_home / "descriptors.yaml")
    shutil.copy(SPEC / "claims.yaml", tmp_home / "claims.yaml")
    ctx = wiring.make_context(tmp_home)
    try:
        plan = init_flow.run_init(ctx, law_dir=tmp_home, skill="python", target_level=2, hours_per_day=1.0,
                                  days=3, deadline=None, goals=["automate scripts"])
        assert plan.slices and (tmp_home / "stacks" / "python" / "plan.json").exists()
        for i, _ in enumerate(plan.slices, start=1):
            assert "RESULT ok" in (tmp_home / "slices" / f"{i:02d}" / "gencheck.log").read_text()
    finally:
        ctx.store.close()
