"""US4: offline queue and blocked attempts (quickstart scenarios 6 and 7)."""

import builders as b
from conftest import write_solution
from typer.testing import CliRunner

from ramp.cli import app
from ramp.loop import submit_flow as sf
from ramp.loop import today_flow
from ramp.providers.port import CostCapExceeded, ProviderFailed, ProviderOffline

runner = CliRunner()


def invoke(cmd, llm, input=None):
    return runner.invoke(app, cmd, obj={"llm": llm}, input=input)


def reviewer_calls(llm):
    return [c for c in llm.calls if c.role == "reviewer"]


def test_offline_submit_queues_the_attempt_and_keeps_the_slice_locked(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [ProviderOffline("no route")]
    out = sf.run_submit(ctx)
    assert out.status == "queued" and not out.passed
    row = ctx.store.get_attempt(out.attempt_id)
    assert row["status"] == "pending_review" and row["passed"] is None and row["review_json"] is None
    assert "wc" in row["diff"] and "[exit 0]" in row["test_output"]
    assert ctx.store.get_slice_state("S1")["status"] == "current"
    assert ctx.store.get_slice_state("S2")["status"] == "locked"


def test_cli_offline_submit_says_queued_and_exits_0(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [ProviderOffline("no route")]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0, res.output
    assert "queued" in res.output.lower() and "today" in res.output.lower()


def test_next_today_drains_the_queue_with_one_line_per_review(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [ProviderOffline("no route")]
    queued = sf.run_submit(ctx)
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    view = today_flow.run_today(ctx)
    assert len(view.drained) == 1 and "S1" in view.drained[0] and "passed" in view.drained[0]
    row = ctx.store.get_attempt(queued.attempt_id)
    assert row["status"] == "reviewed" and row["passed"] == 1 and row["verdict"] == "pass"
    # a drained pass does not unlock: the teach-back (a normal submit) does
    assert ctx.store.get_slice_state("S1")["status"] == "current"
    assert "submit" in view.drained[0]


def test_cli_today_prints_drained_lines_before_the_brief(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home, b.WRONG)
    llm.responses["reviewer"] = [ProviderOffline("no route")]
    sf.run_submit(ctx)
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    llm.responses["grader"] = [b.card_prompt()]
    res = invoke(["today"], llm, input="\n")  # the drained weak concept is due at once; Enter skips its card
    assert res.exit_code == 0, res.output
    assert res.output.index("Reviewed queued") < res.output.index("Slice 1")
    assert "needs work" in res.output.lower()


def test_submit_drains_oldest_first_before_running_the_new_attempt(curriculum):
    ctx, llm = curriculum
    # offline for: the first submit; the second submit's drain (still offline); the second submit itself
    llm.responses["reviewer"] = [ProviderOffline("a"), ProviderOffline("b"), ProviderOffline("c")]
    write_solution(ctx.home, b.WRONG)
    first = sf.run_submit(ctx)
    write_solution(ctx.home)
    second = sf.run_submit(ctx)
    assert first.status == second.status == "queued"
    llm.calls.clear()
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work"),
                                 b.review_out(rating=4)]
    llm.responses["grader"] = [b.card_prompt()]
    out = sf.run_submit(ctx)
    calls = reviewer_calls(llm)
    assert len(out.drained) == 2 and len(calls) == 2  # the new attempt reuses the review of its identical twin
    assert "return {}" in calls[0].user and "out.get" in calls[1].user  # oldest first
    assert out.reused_review and out.passed
    assert [ctx.store.get_attempt(i)["status"] for i in (first.attempt_id, second.attempt_id)] == ["reviewed"] * 2


def test_identical_queued_attempts_cost_one_review(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [ProviderOffline("a"), ProviderOffline("b"), ProviderOffline("c")]
    sf.run_submit(ctx)
    sf.run_submit(ctx)  # its drain is still offline too
    llm.calls.clear()
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    view = today_flow.run_today(ctx)
    assert len(view.drained) == 2 and len(reviewer_calls(llm)) == 1


def test_still_offline_leaves_the_queue_and_queues_the_new_attempt_too(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [ProviderOffline("a")]
    sf.run_submit(ctx)
    llm.responses["reviewer"] = [ProviderOffline("b"), ProviderOffline("c")]
    out = sf.run_submit(ctx)
    assert out.status == "queued"
    assert any("offline" in line.lower() for line in out.drained)
    assert [r["status"] for r in ctx.store.list_attempts("S1")] == ["pending_review", "pending_review"]


def test_provider_failure_blocks_with_cause_and_leaves_passed_null(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home, b.WRONG)
    llm.responses["reviewer"] = [ProviderFailed("provider failed for role 'reviewer'")]
    res = invoke(["submit"], llm)
    assert res.exit_code == 1
    out = " ".join(res.output.split())
    assert "Blocked" in out and "provider" in out and "What to try" in out and "config.toml" in out
    row = ctx.store.list_attempts("S1")[0]
    assert row["status"] == "blocked" and row["passed"] is None and "provider" in row["blocked_cause"]


def test_cost_cap_blocks_the_same_way(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home, b.WRONG)
    llm.responses["reviewer"] = [CostCapExceeded("cap reached")]
    res = invoke(["submit"], llm)
    assert res.exit_code == 1 and "cap" in " ".join(res.output.split())
    assert ctx.store.list_attempts("S1")[0]["status"] == "blocked"


def test_a_later_successful_submit_supersedes_the_blocked_attempt(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [ProviderFailed("down")]
    blocked = sf.run_submit(ctx)
    assert blocked.status == "blocked"
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    ok = sf.run_submit(ctx)
    assert ok.passed and ok.drained == []  # a blocked attempt is history, never drained
    statuses = [r["status"] for r in ctx.store.list_attempts("S1")]
    assert statuses == ["blocked", "reviewed"]


def test_edited_tests_that_collect_nothing_are_needs_work_not_blocked(curriculum):
    """Scenario 7: pytest exit 5 with a changed fingerprint is the learner's doing."""
    ctx, llm = curriculum
    write_solution(ctx.home)
    (ctx.home / "slices" / "01" / "workspace" / "tests" / "test_wc.py").write_text("# emptied\n")
    llm.responses["reviewer"] = [b.review_out(rating=4, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    out = sf.run_submit(ctx)
    assert out.status == "reviewed" and out.fingerprint_changed and not out.passed
