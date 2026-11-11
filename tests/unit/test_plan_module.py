import json
import os

import builders as b
import pytest

from ramp.plan import curriculum, scaffold


def test_plan_json_round_trip(tmp_path):
    from ramp import models as m

    o = b.outline(2)
    plan = m.Plan(skill="python", target_level=2, known={"java": 3}, hours_per_day=1, days=2, deadline=None,
                  goals=[], concepts=o.concepts, cando_map=o.cando_map,
                  slices=[b.slice_for(1), b.slice_for(2)], created_at="2026-11-11T00:00:00+00:00")
    p = tmp_path / "stacks" / "python" / "plan.json"
    curriculum.write_plan(p, plan)
    assert curriculum.read_plan(p) == plan
    assert json.loads(p.read_text())["skill"] == "python"


def test_next_states_unlocks_following_slice():
    states = [("S1", "current"), ("S2", "locked"), ("S3", "locked")]
    assert curriculum.next_states(states, "S1") == [("S1", "passed"), ("S2", "current")]
    assert curriculum.next_states([("S1", "passed"), ("S2", "current"), ("S3", "locked")], "S2") == [
        ("S2", "passed"), ("S3", "current")]


def test_next_states_last_slice_has_nothing_to_unlock():
    assert curriculum.next_states([("S1", "passed"), ("S2", "current")], "S2") == [("S2", "passed")]


def test_next_states_only_current_can_pass():
    with pytest.raises(ValueError):
        curriculum.next_states([("S1", "current"), ("S2", "locked")], "S2")
    with pytest.raises(ValueError):
        curriculum.next_states([("S1", "current")], "S9")


def test_scaffold_creates_layout_and_records_fingerprint(tmp_path):
    d = tmp_path / "slices" / "01"
    fp = scaffold.scaffold_slice(b.slice_for(1), d)
    ws = d / "workspace"
    assert (ws / "tests" / "test_wc.py").read_text() == b.GOOD_TEST
    assert (ws / "fixtures" / "in.txt").exists() and (ws / "src" / "wc" / "__init__.py").exists()
    for sub in ("tests", "fixtures", "expected", "src"):
        assert (ws / sub).is_dir()
    assert (d / "brief.md").read_text().startswith("# Slice 1")
    meta = json.loads((d / "slice.json").read_text())
    assert meta["shipped_fingerprint"] == fp and meta["slice"]["id"] == "S1"
    assert (d / "scaffold" / "src" / "wc" / "__init__.py").exists()  # snapshot used to diff learner work


def test_scaffold_overwrites_previous_attempt(tmp_path):
    d = tmp_path / "slices" / "01"
    scaffold.scaffold_slice(b.slice_for(1), d)
    (d / "workspace" / "stale.txt").write_text("old")
    scaffold.scaffold_slice(b.slice_for(1, test=b.GREEN_TEST), d)
    assert not (d / "workspace" / "stale.txt").exists()
    assert (d / "workspace" / "tests" / "test_wc.py").read_text() == b.GREEN_TEST


def test_scaffold_refuses_path_outside_workspace_and_writes_nothing(tmp_path):
    d = tmp_path / "slices" / "01"
    sl = b.slice_for(1).model_copy(update={"files": {"tests/ok.py": "x", "tests/../../escape.py": "y"}})
    with pytest.raises(scaffold.UnsafeScaffold):
        scaffold.scaffold_slice(sl, d)
    assert not (tmp_path / "slices" / "escape.py").exists()
    assert not (d / "workspace").exists()


def test_scaffold_refuses_to_write_through_symlinks(tmp_path):
    d = tmp_path / "slices" / "01"
    outside = tmp_path / "outside"
    outside.mkdir()
    (d / "workspace").mkdir(parents=True)
    (d / "workspace" / "tests").symlink_to(outside, target_is_directory=True)
    # a stale symlinked workspace is replaced, never followed
    scaffold.scaffold_slice(b.slice_for(1), d)
    assert not (outside / "test_wc.py").exists()
    assert not os.path.islink(d / "workspace" / "tests")


def test_scaffold_symlink_inside_new_tree_is_refused(tmp_path, monkeypatch):
    d = tmp_path / "slices" / "01"
    outside = tmp_path / "outside"
    outside.mkdir()
    sl = b.slice_for(1)
    real = scaffold._prepare_dirs

    def plant(workspace):
        real(workspace)
        (workspace / "src" / "wc").symlink_to(outside, target_is_directory=True)

    monkeypatch.setattr(scaffold, "_prepare_dirs", plant)
    with pytest.raises(scaffold.UnsafeScaffold):
        scaffold.scaffold_slice(sl, d)
    assert list(outside.iterdir()) == []
