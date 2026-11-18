from datetime import UTC, datetime, timedelta

import builders as b
from conftest import write_solution
from typer.testing import CliRunner

from ramp import review
from ramp.cli import app
from ramp.loop import submit_flow as sf
from ramp.loop import today_flow
from ramp.providers.port import ProviderOffline

runner = CliRunner()


def invoke(cmd, llm, input=None):
    return runner.invoke(app, cmd, obj={"llm": llm}, input=input)


def add_due_card(store, concept, question, due):
    c = review.new_card()
    store.add_card(c.card_id, concept, review.card_to_json(c), due.isoformat(), question, "rubric", "t", "weak_review")
    return c.card_id


def make_weak_card(ctx, llm):
    """Fail a review on a green solution so `counter` becomes a card (the prompt upgrade is scripted too)."""
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=2)]
    llm.responses["grader"] = [b.card_prompt(question="Explain Counter in your own words?")]
    out = sf.run_submit(ctx)
    assert not out.passed and out.weak_concepts == ["counter"]


def test_a_new_weak_card_is_due_on_the_next_today_with_the_model_prompt(curriculum):
    ctx, llm = curriculum
    make_weak_card(ctx, llm)
    view = today_flow.run_today(ctx)
    assert [c.question for c in view.cards] == ["Explain Counter in your own words?"]
    assert view.cards[0].concept == "Counter" and view.slice_id == "S1"


def test_due_cards_are_ordered_by_due_ascending_and_future_cards_are_not_served(curriculum):
    ctx, _ = curriculum
    now = datetime.now(UTC)
    store = ctx.store
    store.upsert_concept("c3", "python", "Third", None)
    store.upsert_concept("c4", "python", "Fourth", None)
    add_due_card(store, "counter", "later?", now - timedelta(hours=1))
    add_due_card(store, "eafp", "earlier?", now - timedelta(days=2))
    add_due_card(store, "c3", "future?", now + timedelta(days=2))
    view = today_flow.run_today(ctx)
    assert [c.question for c in view.cards] == ["earlier?", "later?"]


def test_with_no_due_cards_the_brief_is_shown_directly(curriculum):
    ctx, llm = curriculum
    view = today_flow.run_today(ctx)
    assert view.cards == [] and view.brief
    res = invoke(["today"], llm)
    assert res.exit_code == 0 and "Slice 1" in res.output and "Review" not in res.output


def test_cli_serves_cards_before_the_brief_grades_and_reschedules(curriculum):
    ctx, llm = curriculum
    make_weak_card(ctx, llm)
    llm.responses["grader"] = [b.grader_out(4, "Clear and correct.")]
    res = invoke(["today"], llm, input="a dict that counts things\n")
    assert res.exit_code == 0, res.output
    out = res.output
    assert out.index("Explain Counter in your own words?") < out.index("Slice 1")
    assert "Clear and correct." in out and "grade 4" in out.lower()
    rows = ctx.store.list_card_reviews()
    assert len(rows) == 1 and rows[0]["grade"] == 4 and rows[0]["rating"] == 3
    assert rows[0]["answer"] == "a dict that counts things"
    assert datetime.fromisoformat(ctx.store.get_card_by_concept("counter")["due"]) > datetime.now(UTC)
    assert llm.calls[-1].role == "grader" and "a dict that counts things" in llm.calls[-1].user


def test_blank_answer_skips_the_card_without_a_model_call(curriculum):
    ctx, llm = curriculum
    make_weak_card(ctx, llm)
    llm.calls.clear()
    res = invoke(["today"], llm, input="\n")
    assert res.exit_code == 0 and "skipped" in res.output.lower() and "Slice 1" in res.output
    assert llm.calls == [] and ctx.store.count_card_reviews() == 0
    assert today_flow.run_today(ctx).cards  # still due


def test_provider_failure_while_grading_keeps_the_card_due_and_today_still_works(curriculum):
    ctx, llm = curriculum
    make_weak_card(ctx, llm)
    llm.responses["grader"] = [ProviderOffline("no route")]
    res = invoke(["today"], llm, input="my answer\n")
    assert res.exit_code == 0, res.output
    assert "could not grade" in res.output.lower() and "Slice 1" in res.output
    assert ctx.store.count_card_reviews() == 0 and len(today_flow.run_today(ctx).cards) == 1


def test_finished_curriculum_says_no_level_is_recorded(curriculum):
    ctx, llm = curriculum
    for sid in ("S1", "S2"):
        ctx.store.set_slice_state(sid, "python", "passed", "t")
    res = invoke(["today"], llm)
    assert res.exit_code == 0 and "finished" in res.output.lower() and "no level" in res.output.lower()


def test_cards_are_still_served_after_the_curriculum_is_finished(curriculum):
    ctx, llm = curriculum
    for sid in ("S1", "S2"):
        ctx.store.set_slice_state(sid, "python", "passed", "t")
    add_due_card(ctx.store, "counter", "still due?", datetime.now(UTC) - timedelta(days=1))
    llm.responses["grader"] = [b.grader_out(5)]
    res = invoke(["today"], llm, input="answer\n")
    assert res.exit_code == 0 and "still due?" in res.output and "finished" in res.output.lower()


def test_a_grader_rationale_that_contains_code_is_replaced_but_the_grade_stays(curriculum):
    ctx, llm = curriculum
    make_weak_card(ctx, llm)
    llm.responses["grader"] = [b.grader_out(2, "Use ```d = {}``` instead.")]
    res = invoke(["today"], llm, input="x\n")
    assert res.exit_code == 0 and "```" not in res.output and "Grade 2/5" in res.output
    row = ctx.store.list_card_reviews()[0]
    assert row["grade"] == 2 and "```" not in row["rationale"]
