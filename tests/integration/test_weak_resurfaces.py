"""DoD #3: at least two struggled concepts resurface as reviews and are graded."""

from datetime import UTC, datetime

import builders as b
from conftest import write_solution
from typer.testing import CliRunner

from ramp.cli import app, wiring
from ramp.loop import init_flow
from ramp.providers.port import FakeLLM

runner = CliRunner()


def invoke(cmd, llm, input=None):
    return runner.invoke(app, cmd, obj={"llm": llm}, input=input)


def test_two_weak_concepts_become_cards_resurface_and_are_graded(law_home):
    llm = FakeLLM({"planner": [b.eligible(), b.two_concept_outline(2)], "writer": [b.draft_for(1), b.draft_for(2)]})
    ctx = wiring.make_context(law_home, llm=llm)
    init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=2, hours_per_day=1.0, days=1,
                       deadline=None, goals=[])
    llm.calls.clear()
    write_solution(law_home)

    # submit: green tests, but both target concepts rated low -> not a pass, two weak cards
    llm.responses["reviewer"] = [b.review_out(rating=2, concepts=("counter", "eafp"))]
    llm.responses["grader"] = [b.card_prompt(question="Explain Counter?"), b.card_prompt(question="Explain EAFP?")]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0, res.output
    assert {r["concept_id"] for r in ctx.store.all_cards()} == {"counter", "eafp"}

    # next today: both cards come first, are graded, rescheduled
    llm.responses["grader"] = [b.grader_out(4, "Good."), b.grader_out(2, "Thin.")]
    res = invoke(["today"], llm, input="answer one\nanswer two\n")
    assert res.exit_code == 0, res.output
    out = res.output
    assert out.index("Explain Counter?") < out.index("Slice 1") and out.index("Explain EAFP?") < out.index("Slice 1")
    reviews = ctx.store.list_card_reviews()
    assert len(reviews) == 2 and {r["grade"] for r in reviews} == {4, 2}
    assert {r["rating"] for r in reviews} == {3, 2}
    now = datetime.now(UTC)
    assert all(datetime.fromisoformat(c["due"]) > now for c in ctx.store.all_cards())

    # and nothing is due on an immediate second today
    llm.calls.clear()
    res = invoke(["today"], llm)
    assert res.exit_code == 0 and "Explain" not in res.output and llm.calls == []
    ctx.store.close()
