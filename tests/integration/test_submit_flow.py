import builders as b
import pytest
from conftest import write_solution

from ramp.loop import submit_flow as sf
from ramp.loop import today_flow
from ramp.providers.port import ProviderFailed
from ramp.runner.exec import RunResult


def R(code, pytest_cmd=True, **kw):
    return RunResult(argv=["pytest"], exit_code=code, output="out", is_pytest=pytest_cmd, **kw)


# ---- classify_run (data-model.md §6)
@pytest.mark.parametrize("results,shipped,now,expect", [
    ([R(None, timed_out=True)], "a", "a", ("blocked", "timeout")),
    ([R(None, start_failed=True)], "a", "a", ("blocked", "start")),
    ([R(5)], "a", "a", ("blocked", "pytest exit 5")),
    ([R(2)], "a", "a", ("blocked", "pytest exit 2")),
    ([R(3)], "a", "a", ("blocked", "pytest exit 3")),
    ([R(4)], "a", "a", ("blocked", "pytest exit 4")),
    ([R(5)], "a", "b", ("failed", None)),
    ([R(2)], "a", "b", ("failed", None)),
    ([R(1)], "a", "a", ("failed", None)),
    ([R(1, pytest_cmd=False)], "a", "a", ("failed", None)),
    ([R(2, pytest_cmd=False)], "a", "a", ("failed", None)),
    ([R(0), R(1)], "a", "a", ("failed", None)),
    ([R(0), R(0)], "a", "a", ("green", None)),
])
def test_classify_run(results, shipped, now, expect):
    kind, cause = sf.classify_run(results, shipped, now)
    assert kind == expect[0]
    if expect[1]:
        assert expect[1] in cause


# ---- today
def test_today_shows_brief_bridges_and_workspace(curriculum):
    ctx, _ = curriculum
    t = today_flow.run_today(ctx)
    assert t.slice_id == "S1" and t.title == "Slice 1"
    assert len(t.brief.split()) <= 150 and "```" not in t.brief
    assert t.bridges and "java" in t.bridges[0].lower()
    assert str(ctx.home / "slices" / "01" / "workspace") == t.workspace


def test_today_with_finished_curriculum(curriculum):
    ctx, _ = curriculum
    ctx.store.set_slice_state("S1", "python", "passed")
    ctx.store.set_slice_state("S2", "python", "passed")
    t = today_flow.run_today(ctx)
    assert t.finished and "no level" in t.message.lower()


def test_today_without_curriculum(law_home):
    from ramp.cli import wiring

    ctx = wiring.make_context(law_home, llm=None)
    try:
        with pytest.raises(today_flow.NoCurriculum):
            today_flow.run_today(ctx)
    finally:
        ctx.store.close()


# ---- submit
def test_wrong_code_gets_locate_only_hints(curriculum):
    ctx, llm = curriculum
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    out = sf.run_submit(ctx)
    assert out.status == "reviewed" and out.verdict == "needs_work" and not out.passed
    assert [i.hint for i in out.issues] == [b.CLEAN_ISSUE[2]]
    row = ctx.store.get_attempt(out.attempt_id)
    assert row["passed"] == 0 and row["status"] == "reviewed" and row["hints_used"] == 1
    assert "1 failed" in row["test_output"] or "failed" in row["test_output"]
    assert ctx.store.get_slice_state("S1")["status"] == "current"


def test_correct_code_with_good_ratings_passes_and_unlocks(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    out = sf.run_submit(ctx)
    assert out.passed and out.verdict == "pass" and out.unlocked == "S2"
    assert ctx.store.get_attempt(out.attempt_id)["passed"] == 1
    assert ctx.store.get_slice_state("S1")["status"] == "passed"
    assert ctx.store.get_slice_state("S2")["status"] == "current"


def test_green_tests_with_a_low_rating_is_not_a_pass_and_makes_a_card(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=2, verdict="pass")]
    out = sf.run_submit(ctx)
    assert not out.passed and out.verdict == "needs_work"
    assert ctx.store.get_card_by_concept("counter") is not None
    assert ctx.store.get_slice_state("S2")["status"] == "locked"


def test_leaked_solution_never_passes(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=5, leaked=True)]
    assert not sf.run_submit(ctx).passed


def test_reviewer_receives_brief_diff_and_test_output(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    sf.run_submit(ctx)
    user = llm.calls[0].user
    assert "Count the words in a file" in user and "+def count(text):" in user and "passed" in user


def test_lint_violation_is_regenerated_then_clean_hint_is_kept(curriculum):
    ctx, llm = curriculum
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CODE_ISSUE], verdict="needs_work"),
                                 b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    out = sf.run_submit(ctx)
    assert len(llm.calls) == 2 and "L2" in llm.calls[1].user
    assert [i.hint for i in out.issues] == [b.CLEAN_ISSUE[2]]


def test_three_violations_fall_back_to_a_generic_hint_without_code(curriculum):
    ctx, llm = curriculum
    fence = ("src/wc/__init__.py:1", "returns nothing", "```python\nreturn {}\n```")
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CODE_ISSUE, fence], verdict="needs_work")] * 3
    out = sf.run_submit(ctx)
    assert len(llm.calls) == 3  # 1 try + max_regenerations (2)
    from ramp.lint.leak import check_hint

    for issue in out.issues:
        assert check_hint(issue.hint, issue.location).ok and "replace the loop" not in issue.hint
    stored = ctx.store.get_attempt(out.attempt_id)["review_json"]
    assert "```" not in stored and "comprehension" not in stored


def test_pytest_exit_5_with_unchanged_fingerprint_is_blocked_and_not_reviewed(curriculum, monkeypatch):
    ctx, llm = curriculum
    monkeypatch.setattr(sf.rexec, "run_argv", lambda v, w, timeout_s=30: R(5))
    out = sf.run_submit(ctx)
    assert out.status == "blocked" and "exit 5" in out.blocked_cause and llm.calls == []
    row = ctx.store.get_attempt(out.attempt_id)
    assert row["status"] == "blocked" and row["passed"] is None and row["review_json"] is None
    assert row["fingerprint_changed"] == 0


def test_edited_tests_turn_the_same_failure_into_needs_work(curriculum):
    ctx, llm = curriculum
    (ctx.home / "slices" / "01" / "workspace" / "tests" / "test_wc.py").write_text("def helper():\n    pass\n")
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    out = sf.run_submit(ctx)
    assert out.status == "reviewed" and out.verdict == "needs_work"
    assert ctx.store.get_attempt(out.attempt_id)["fingerprint_changed"] == 1


def test_provider_failure_is_blocked_with_cause(curriculum):
    ctx, llm = curriculum
    llm.responses["reviewer"] = [ProviderFailed("provider failed for role 'reviewer'")]
    out = sf.run_submit(ctx)
    assert out.status == "blocked" and "provider" in out.blocked_cause
    row = ctx.store.get_attempt(out.attempt_id)
    assert row["status"] == "blocked" and row["passed"] is None
    assert "failed" in row["test_output"] or row["test_output"]  # test output is kept


def test_blocked_attempt_is_cleared_by_submitting_again(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [ProviderFailed("down"), b.review_out(rating=4)]
    first = sf.run_submit(ctx)
    second = sf.run_submit(ctx)
    assert first.status == "blocked" and second.passed
    assert len(ctx.store.list_attempts("S1")) == 2


def test_attempt_stores_the_acceptance_fingerprint(curriculum):
    import json

    ctx, llm = curriculum
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    out = sf.run_submit(ctx)
    shipped = json.loads((ctx.home / "slices" / "01" / "slice.json").read_text())["shipped_fingerprint"]
    assert ctx.store.get_attempt(out.attempt_id)["fingerprint"] == shipped


def test_submit_without_curriculum_or_after_the_end(curriculum, law_home):
    ctx, _ = curriculum
    ctx.store.set_slice_state("S1", "python", "passed")
    ctx.store.set_slice_state("S2", "python", "passed")
    with pytest.raises(sf.NothingToSubmit):
        sf.run_submit(ctx)
