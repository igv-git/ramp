"""T078: the Definition-of-Done facts the logs and stored data must prove (DoD #4 and #10)."""

import json
import re
from pathlib import Path

import builders as b
from conftest import write_solution

from ramp.lint.leak import check_hint
from ramp.loop import submit_flow as sf

EVAL = Path(__file__).resolve().parent.parent / "eval" / "leak_eval.jsonl"
FENCE = re.compile(r"```|~~~")


def test_zero_lint_violations_on_the_eval_set():
    rows = [json.loads(line) for line in EVAL.read_text().splitlines() if line]
    wrong = [r["id"] for r in rows if check_hint(r["hint"], r["location"]).ok != (r["label"] == "pass")]
    assert len(rows) >= 40 and wrong == []


def test_every_shipped_slice_has_a_passing_gencheck_log(curriculum):
    ctx, _ = curriculum
    logs = sorted((ctx.home / "slices").glob("*/gencheck.log"))
    assert len(logs) == len(ctx.store.list_slice_states()) == 2
    for log in logs:
        results = [line for line in log.read_text().splitlines() if line.startswith("RESULT")]
        assert results and results[-1].startswith("RESULT ok"), log


def test_a_regenerated_slice_still_ends_with_a_passing_log(law_home):
    from ramp.cli import wiring
    from ramp.loop import init_flow
    from ramp.providers.port import FakeLLM

    llm = FakeLLM({"planner": [b.eligible(), b.outline(1, 30)],
                   "writer": [b.draft_for(1, test=b.GREEN_TEST), b.draft_for(1)]})
    ctx = wiring.make_context(law_home, llm=llm)
    init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=2, hours_per_day=1.0, days=1,
                       goals=[])
    results = [line for line in (law_home / "slices" / "01" / "gencheck.log").read_text().splitlines()
               if line.startswith("RESULT")]
    assert [r.split()[1] for r in results] == ["fail", "ok"]
    ctx.store.close()


def test_no_stored_review_contains_a_code_block_even_when_the_model_sent_one(curriculum):
    ctx, llm = curriculum
    fence = ("src/wc/__init__.py:1", "count returns nothing", "At src/wc/__init__.py:1 use ```d = {}``` here.")
    dirty = b.review_out(rating=1, issues=[b.CODE_ISSUE, fence], verdict="needs_work")
    dirty = dirty.model_copy(update={"understanding_check": "What does ```return {}``` do?"})
    write_solution(ctx.home, b.WRONG)
    llm.responses["reviewer"] = [dirty] * 3  # 1 try + 2 regenerations, then the generic fallback
    llm.responses["grader"] = [b.card_prompt()]
    sf.run_submit(ctx)
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    sf.run_submit(ctx)
    stored = [r["review_json"] for r in ctx.store.list_attempts() if r["review_json"]]
    assert len(stored) == 2
    assert all(not FENCE.search(text) for text in stored)
    assert all("```" not in json.loads(t)["understanding_check"] for t in stored)


def test_stored_issues_pass_the_hint_lint(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home, b.WRONG)
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CODE_ISSUE], verdict="needs_work")] * 3
    llm.responses["grader"] = [b.card_prompt()]
    sf.run_submit(ctx)
    review = json.loads(ctx.store.list_attempts("S1")[0]["review_json"])
    for issue in review["issues"]:
        assert check_hint(issue["hint"], issue["location"]).ok
