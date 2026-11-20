import builders as b
from conftest import write_solution
from typer.testing import CliRunner

from ramp.cli import app
from ramp.loop import submit_flow as sf
from ramp.providers.port import ProviderOffline

runner = CliRunner()


def invoke(cmd, llm, input=None):
    return runner.invoke(app, cmd, obj={"llm": llm}, input=input)


def passing_submit(ctx, llm, rating=4):
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=rating)]
    out = sf.run_submit(ctx)
    assert out.passed
    return out


def test_a_pass_requests_a_teachback_and_does_not_unlock_yet(curriculum):
    ctx, llm = curriculum
    out = passing_submit(ctx, llm)
    assert out.needs_teachback and out.unlocked is None
    assert "Why does the key for a missing word start at zero?" in out.teachback_question
    assert ctx.store.get_slice_state("S1")["status"] == "current"
    assert ctx.store.get_slice_state("S2")["status"] == "locked"
    assert ctx.store.get_teachback(out.attempt_id) is None


def test_a_failed_attempt_never_asks_for_a_teachback(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home, b.WRONG)
    llm.responses["grader"] = [b.card_prompt()]  # the weak concept gets a model-written card
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    out = sf.run_submit(ctx)
    assert not out.needs_teachback and out.teachback_question == ""


def test_teachback_is_stored_graded_through_the_gate_and_unlocks_the_next_slice(curriculum):
    ctx, llm = curriculum
    out = passing_submit(ctx, llm)
    llm.responses["grader"] = [b.grader_out(4, "Solid explanation.")]
    tb = sf.complete_teachback(ctx, out, "The dict get default makes missing words zero")
    tbrow = ctx.store.get_teachback(out.attempt_id)
    assert tbrow["answer"] == "The dict get default makes missing words zero" and tbrow["grade"] == 4
    assert tb.grade == 4 and tb.rationale == "Solid explanation." and tb.unlocked == "S2"
    assert ctx.store.get_slice_state("S1")["status"] == "passed"
    assert ctx.store.get_slice_state("S2")["status"] == "current"
    call = llm.calls[-1]
    assert call.role == "grader" and "Why does the key for a missing word start at zero?" in call.user
    assert "The dict get default" in call.user and "Count the words" in call.user


def test_weak_teachback_creates_a_card_for_the_slice_concepts(curriculum):
    ctx, llm = curriculum
    out = passing_submit(ctx, llm)
    llm.responses["grader"] = [b.grader_out(1, "Too vague."), b.card_prompt(question="Explain Counter?")]
    tb = sf.complete_teachback(ctx, out, "it counts")
    assert tb.cards_created == ["counter"] and tb.unlocked == "S2"
    card = ctx.store.get_card_by_concept("counter")
    assert card["created_reason"] == "weak_teachback" and card["question"] == "Explain Counter?"


def test_grader_outage_still_stores_the_teachback_and_unlocks(curriculum):
    ctx, llm = curriculum
    out = passing_submit(ctx, llm)
    llm.responses["grader"] = [ProviderOffline("no route")]
    tb = sf.complete_teachback(ctx, out, "my explanation")
    assert tb.grade is None and tb.unlocked == "S2"
    assert ctx.store.get_teachback(out.attempt_id)["answer"] == "my explanation"
    assert ctx.store.get_teachback(out.attempt_id)["grade"] is None


def test_cli_pass_prompts_for_the_teachback_then_unlocks(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    llm.responses["grader"] = [b.grader_out(4, "Solid explanation.")]
    res = invoke(["submit"], llm, input="because get has a default\n")
    assert res.exit_code == 0, res.output
    out = res.output
    assert "Passed" in out and "teach-back" in out.lower()
    assert out.index("Why does the key for a missing word start at zero?") < out.index("Solid explanation.")
    assert "S2" in out and "unlocked" in out.lower()
    assert ctx.store.get_slice_state("S2")["status"] == "current"


def test_cli_abort_before_the_answer_leaves_the_slice_current_and_resubmit_costs_nothing(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    res = invoke(["submit"], llm, input="")  # no answer at all: the prompt aborts
    assert res.exit_code != 0 and "ramp submit" in res.output
    assert ctx.store.get_slice_state("S1")["status"] == "current"
    assert ctx.store.get_slice_state("S2")["status"] == "locked"
    llm.calls.clear()
    llm.responses["grader"] = [b.grader_out(3)]
    res = invoke(["submit"], llm, input="my explanation\n")
    assert res.exit_code == 0, res.output
    assert [c.role for c in llm.calls] == ["grader"]  # same code and output: the review is reused
    assert ctx.store.get_slice_state("S2")["status"] == "current"


def test_cli_last_slice_teachback_says_the_curriculum_is_done(curriculum):
    ctx, llm = curriculum
    ctx.store.set_slice_state("S1", "python", "passed", "t")
    ctx.store.set_slice_state("S2", "python", "current")
    write_solution(ctx.home, slice_no="02")
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    llm.responses["grader"] = [b.grader_out(5)]
    res = invoke(["submit"], llm, input="explained\n")
    assert res.exit_code == 0, res.output
    assert "last slice" in res.output.lower()
    assert ctx.store.get_slice_state("S2")["status"] == "passed"
