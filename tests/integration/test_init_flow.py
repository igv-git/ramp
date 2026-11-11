import builders as b
import pytest

from ramp import models as m
from ramp.cli import wiring
from ramp.loop import init_flow
from ramp.matrix import LawError
from ramp.providers.port import FakeLLM


def run(law_home, llm, **over):
    ctx = wiring.make_context(law_home, llm=llm)
    args = {"skill": "python", "target_level": 2, "hours_per_day": 1.0, "days": 1, "deadline": None, "goals": []}
    args.update(over)
    try:
        return init_flow.run_init(ctx, law_dir=law_home, **args), ctx
    finally:
        pass


def nothing_written(law_home, ctx):
    assert not (law_home / "stacks").exists() and not (law_home / "slices").exists()
    assert ctx.store.list_concepts() == [] and ctx.store.list_slice_states() == []


def test_success_writes_plan_slices_and_state(law_home):
    llm = FakeLLM({"planner": [b.eligible(), b.outline(2, 30)], "writer": [b.slice_for(1), b.slice_for(2)]})
    plan, ctx = run(law_home, llm)
    try:
        assert [s.id for s in plan.slices] == ["S1", "S2"]
        assert (law_home / "stacks" / "python" / "plan.json").exists()
        for n in ("01", "02"):
            d = law_home / "slices" / n
            assert (d / "slice.json").exists() and (d / "brief.md").exists()
            assert "RESULT ok" in (d / "gencheck.log").read_text()
        assert [(r["slice_id"], r["status"]) for r in ctx.store.list_slice_states()] == [
            ("S1", "current"), ("S2", "locked")]
        assert ctx.store.get_concept("counter") is not None
        assert plan.known == {"java": 3, "sql": 1, "js": 1}  # claims used only as bridge fuel
        assert [c.role for c in llm.calls] == ["planner", "planner", "writer", "writer"]
    finally:
        ctx.store.close()


def test_mock_descriptors_refused_and_nothing_written(law_home):
    text = (law_home / "descriptors.yaml").read_text().replace("status: approved", "status: mock")
    (law_home / "descriptors.yaml").write_text(text)
    llm = FakeLLM({})
    ctx = wiring.make_context(law_home, llm=llm)
    try:
        with pytest.raises(LawError, match="mock"):
            init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=2, hours_per_day=1,
                               days=1, deadline=None, goals=[])
        assert llm.calls == []
        nothing_written(law_home, ctx)
    finally:
        ctx.store.close()


def test_unknown_skill_or_level_is_refused_for_now(law_home):
    ctx = wiring.make_context(law_home, llm=FakeLLM({}))
    try:
        with pytest.raises(LawError, match="rust"):
            init_flow.run_init(ctx, law_dir=law_home, skill="rust", target_level=2, hours_per_day=1, days=1,
                               deadline=None, goals=[])
        with pytest.raises(LawError, match="level 9"):
            init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=9, hours_per_day=1,
                               days=1, deadline=None, goals=[])
        nothing_written(law_home, ctx)
    finally:
        ctx.store.close()


def test_ineligible_skill_refused_with_reasons_and_nothing_written(law_home):
    llm = FakeLLM({"planner": [b.eligible(False, ["needs a GPU cluster"])]})
    ctx = wiring.make_context(law_home, llm=llm)
    try:
        with pytest.raises(init_flow.InitRefused) as ei:
            init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=2, hours_per_day=1,
                               days=1, deadline=None, goals=[])
        assert "needs a GPU cluster" in ei.value.reasons
        assert [c.role for c in llm.calls] == ["planner"]
        nothing_written(law_home, ctx)
    finally:
        ctx.store.close()


def test_slice_failing_generation_check_is_regenerated_then_succeeds(law_home):
    llm = FakeLLM({"planner": [b.eligible(), b.outline(1, 30)],
                   "writer": [b.slice_for(1, test=b.GREEN_TEST), b.slice_for(1)]})
    plan, ctx = run(law_home, llm)
    try:
        writer_calls = [c for c in llm.calls if c.role == "writer"]
        assert len(writer_calls) == 2
        assert "green" in writer_calls[1].user  # the check's cause is fed back to the writer
        log = (law_home / "slices" / "01" / "gencheck.log").read_text()
        assert log.count("RESULT fail") == 1 and log.count("RESULT ok") == 1
        assert plan.slices[0].files["tests/test_wc.py"] == b.GOOD_TEST
    finally:
        ctx.store.close()


def test_three_bad_slices_stop_loudly_with_the_cause(law_home):
    bad = b.slice_for(1, test=b.GREEN_TEST)
    llm = FakeLLM({"planner": [b.eligible(), b.outline(1, 30)], "writer": [bad, bad, bad, bad]})
    ctx = wiring.make_context(law_home, llm=llm)
    try:
        with pytest.raises(init_flow.SliceGenerationError) as ei:
            init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=2, hours_per_day=1,
                               days=1, deadline=None, goals=[])
        assert "green" in ei.value.cause and ei.value.slice_id == "S1"
        assert len([c for c in llm.calls if c.role == "writer"]) == 3  # 1 try + max_regenerations (2)
        assert ctx.store.list_slice_states() == []  # nothing recorded as a curriculum
        assert not (law_home / "stacks").exists()
    finally:
        ctx.store.close()


def test_allowlist_violation_in_writer_output_counts_as_failed_check(law_home):
    bad = b.slice_for(1, argv=("sh", "-c", "echo hi"))
    llm = FakeLLM({"planner": [b.eligible(), b.outline(1, 30)], "writer": [bad, b.slice_for(1)]})
    plan, ctx = run(law_home, llm)
    try:
        assert "allowlist" in [c for c in llm.calls if c.role == "writer"][1].user
        assert plan.slices[0].acceptance[0].argv == ["pytest", "-q"]
    finally:
        ctx.store.close()


def test_over_budget_plan_is_regenerated(law_home):
    llm = FakeLLM({"planner": [b.eligible(), b.outline(2, 40), b.outline(2, 30)],
                   "writer": [b.slice_for(1), b.slice_for(2)]})
    plan, ctx = run(law_home, llm)
    try:
        planner_calls = [c for c in llm.calls if c.role == "planner"]
        assert len(planner_calls) == 3 and "minutes" in planner_calls[2].user
        assert sum(s.est_minutes for s in plan.slices) <= 60
    finally:
        ctx.store.close()


def test_writer_cannot_change_identity_of_a_slice(law_home):
    llm = FakeLLM({"planner": [b.eligible(), b.outline(2, 30)], "writer": [b.slice_for(2), b.slice_for(1)]})
    plan, ctx = run(law_home, llm)
    try:
        assert [s.id for s in plan.slices] == ["S1", "S2"] and isinstance(plan, m.Plan)
    finally:
        ctx.store.close()


def test_second_init_never_overwrites_progress(law_home):
    llm = FakeLLM({"planner": [b.eligible(), b.outline(1, 30)], "writer": [b.slice_for(1)]})
    _, ctx = run(law_home, llm)
    try:
        before = (law_home / "stacks" / "python" / "plan.json").read_text()
        with pytest.raises(init_flow.InitRefused, match="already exists"):
            init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=2, hours_per_day=1,
                               days=1, deadline=None, goals=[])
        assert (law_home / "stacks" / "python" / "plan.json").read_text() == before
    finally:
        ctx.store.close()
