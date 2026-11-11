import builders as b
import pytest
from pydantic import ValidationError

from ramp import gate
from ramp import models as m
from ramp.store import db as store_db
from ramp.store.repos import Store


@pytest.fixture
def store(tmp_home):
    s = Store(store_db.connect(tmp_home / "profile.db"))
    yield s
    s.close()


def make_plan(n=2, **over):
    o = b.outline(n)
    kw = {"skill": "python", "target_level": 2, "known": {"java": 3}, "hours_per_day": 1, "days": 2,
          "deadline": None, "goals": [], "concepts": o.concepts, "cando_map": o.cando_map,
          "slices": [b.slice_for(i) for i in range(1, n + 1)], "created_at": "2026-11-11T00:00:00+00:00"}
    kw.update(over)
    return m.Plan(**kw)


def test_apply_plan_writes_concepts_slice_states_and_plan_json(store, tmp_path):
    p = tmp_path / "stacks" / "python" / "plan.json"
    gate.apply_plan(store, make_plan(3), p)
    assert p.exists()
    assert store.get_concept("counter")["name"] == "Counter"
    assert [(r["slice_id"], r["status"]) for r in store.list_slice_states()] == [
        ("S1", "current"), ("S2", "locked"), ("S3", "locked")]


def test_apply_plan_rejects_unvalidated_garbage(store, tmp_path):
    bad = make_plan().model_copy(update={"hours_per_day": -1})
    with pytest.raises(ValidationError):
        gate.apply_plan(store, bad, tmp_path / "plan.json")
    assert store.list_slice_states() == [] and not (tmp_path / "plan.json").exists()


def test_apply_plan_does_not_reset_existing_progress(store, tmp_path):
    gate.apply_plan(store, make_plan(2), tmp_path / "a" / "plan.json")
    with pytest.raises(gate.PlanExists):
        gate.apply_plan(store, make_plan(2), tmp_path / "b" / "plan.json")


def test_apply_slice_scaffolds_and_returns_fingerprint(tmp_path):
    fp = gate.apply_slice(b.slice_for(1), tmp_path / "slices" / "01")
    assert len(fp) == 64 and (tmp_path / "slices" / "01" / "workspace" / "tests" / "test_wc.py").exists()


def test_apply_slice_revalidates_and_writes_nothing_on_unsafe_key(tmp_path):
    sl = b.slice_for(1).model_copy(update={"files": {"tests/../../x.py": "y"}})
    d = tmp_path / "slices" / "01"
    with pytest.raises(ValidationError):
        gate.apply_slice(sl, d)
    assert not d.exists()
