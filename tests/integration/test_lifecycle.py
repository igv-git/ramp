"""T078: quickstart scenarios 1-12 end to end through the CLI with scripted agents (13, the holdout, is human-owned)."""

import json

import builders as b
import pytest
from conftest import write_solution
from typer.testing import CliRunner

from ramp import models as m
from ramp import paths
from ramp.cli import app, wiring
from ramp.providers.port import FakeLLM, ProviderOffline

runner = CliRunner()
INIT = ["init", "--skill", "python", "--to", "2", "--hours", "1", "--days", "1"]


def invoke(cmd, llm, input=None):
    return runner.invoke(app, cmd, obj={"llm": llm}, input=input)


def init_llm(draft_kwargs=None, n=2):
    return FakeLLM({"planner": [b.eligible(), b.outline(n, 30)],
                    "writer": [b.draft_for(i, **(draft_kwargs or {})) for i in range(1, n + 1)]})


def flat(res):
    return " ".join(res.output.split())


def test_1_init_today_wrong_then_right_then_teachback_unlocks_the_next_slice(law_home):
    llm = init_llm()
    res = invoke(INIT, llm)
    assert res.exit_code == 0, res.output
    assert "Slice 1" in invoke(["today"], llm).output
    write_solution(law_home, b.WRONG)
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    llm.responses["grader"] = [b.card_prompt()]
    res = invoke(["submit"], llm)
    assert "needs work" in res.output.lower() and "Hint:" in res.output and "```" not in res.output
    write_solution(law_home)
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    llm.responses["grader"] = [b.grader_out(4)]
    res = invoke(["submit"], llm, input="the dict default makes missing words zero\n")
    assert res.exit_code == 0, res.output
    ctx = wiring.make_context(law_home, llm=llm)
    assert ctx.store.get_slice_state("S1")["status"] == "passed" and ctx.store.get_slice_state("S2")["status"] == "current"
    ctx.store.close()


def test_2_green_tests_with_a_concept_rated_2_is_not_a_pass(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=2, verdict="pass")]
    llm.responses["grader"] = [b.card_prompt()]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0 and "Passed" not in res.output
    assert ctx.store.get_slice_state("S1")["status"] == "current"


def test_3_a_leaked_solution_never_passes(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=5, leaked=True, verdict="pass")]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0 and "Passed" not in res.output
    assert ctx.store.get_slice_state("S2")["status"] == "locked"


def test_4_a_weak_concept_card_is_served_first_on_the_next_today(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=2)]
    llm.responses["grader"] = [b.card_prompt(question="Explain Counter again?")]
    invoke(["submit"], llm)
    res = invoke(["today"], llm, input="\n")
    assert res.output.index("Explain Counter again?") < res.output.index("Slice 1")


@pytest.mark.parametrize("grade,rating", [(2, 2), (4, 3), (5, 4)])
def test_5_a_graded_card_is_rated_rescheduled_and_logged(curriculum, grade, rating):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=2)]
    llm.responses["grader"] = [b.card_prompt()]
    invoke(["submit"], llm)
    before = ctx.store.get_card_by_concept("counter")["due"]
    llm.responses["grader"] = [b.grader_out(grade)]
    invoke(["today"], llm, input="my answer\n")
    row = ctx.store.list_card_reviews()[0]
    assert (row["grade"], row["rating"]) == (grade, rating)
    assert ctx.store.get_card_by_concept("counter")["due"] > before


def test_6_a_connection_failure_queues_the_attempt_and_the_next_today_drains_it(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [ProviderOffline("no route")]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0 and "queued" in res.output.lower()
    assert ctx.store.get_slice_state("S2")["status"] == "locked"
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    res = invoke(["today"], llm)
    assert "Reviewed queued attempt" in res.output
    assert ctx.store.list_attempts("S1")[0]["status"] == "reviewed"


def test_7_pytest_exit_5_is_blocked_unless_the_tests_were_edited(curriculum, monkeypatch):
    from ramp.loop import submit_flow as sf
    from ramp.runner.exec import RunResult

    ctx, llm = curriculum
    write_solution(ctx.home)
    monkeypatch.setattr(sf.rexec, "run_argv", lambda v, ws: RunResult(argv=v.argv, exit_code=5, output="no tests ran",
                                                                      is_pytest=True))
    res = invoke(["submit"], llm)
    assert res.exit_code == 1 and "Blocked" in res.output and "exit 5" in flat(res)
    assert ctx.store.list_attempts("S1")[0]["status"] == "blocked"
    (ctx.home / "slices" / "01" / "workspace" / "tests" / "test_wc.py").write_text("# edited\n")
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    llm.responses["grader"] = [b.card_prompt()]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0 and "needs work" in res.output.lower()
    assert ctx.store.list_attempts("S1")[-1]["fingerprint_changed"] == 1


def test_8_uncollectable_or_all_green_tests_are_regenerated_then_init_stops_loudly(law_home):
    llm = FakeLLM({"planner": [b.eligible(), b.outline(1, 30)],
                   "writer": [b.draft_for(1, test=b.GREEN_TEST)] * 3})
    res = invoke(INIT, llm)
    assert res.exit_code == 1 and "S1" in res.output
    log = (paths.slice_dir(1, law_home) / "gencheck.log").read_text()
    assert log.count("RESULT fail") == 3 and "RESULT ok" not in log  # 1 try + 2 regenerations
    assert not paths.plan_path("python", law_home).exists()


def test_9_a_shell_acceptance_command_is_refused_and_never_executed(law_home, tmp_path):
    marker = tmp_path / "must-not-exist"
    bad = b.draft_for(1).model_copy(update={"acceptance": [m.AcceptanceCommand(argv=["sh", "-c", f"touch {marker}"])]})
    llm = FakeLLM({"planner": [b.eligible(), b.outline(1, 30)], "writer": [bad] * 3})
    res = invoke(INIT, llm)
    assert res.exit_code == 1 and not marker.exists()
    assert not paths.plan_path("python", law_home).exists()


def test_10_an_unknown_skill_is_refused_with_the_defined_skills_and_how_to_add_one(law_home):
    llm = init_llm()
    res = invoke(["init", "--skill", "rust", "--to", "1", "--hours", "1", "--days", "1"], llm)
    text = flat(res)
    assert res.exit_code == 1 and "rust" in text and "python" in text and "README" in text
    assert llm.calls == [] and not paths.plan_path("rust", law_home).exists()


def test_11_export_runs_and_a_forced_failure_in_today_does_not_fail_the_command(curriculum):
    ctx, llm = curriculum
    assert invoke(["export"], llm).exit_code == 0 and (ctx.home / "exports" / "attempts.jsonl").exists()
    import shutil

    shutil.rmtree(ctx.home / "exports")
    (ctx.home / "exports").write_text("in the way")
    res = invoke(["today"], llm)
    assert res.exit_code == 0 and "export failed" in res.output and "Slice 1" in res.output
    assert invoke(["export"], llm).exit_code == 1


def test_12_flag_bridge_valid_is_stored_and_exported_invalid_exits_2(curriculum):
    ctx, llm = curriculum
    assert invoke(["flag-bridge", "S1", "1", "--note", "misleading"], llm).exit_code == 0
    lines = (ctx.home / "exports" / "bridge_flags.jsonl").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["slice_id"] == "S1"
    assert invoke(["flag-bridge", "S1", "5"], llm).exit_code == 2
    assert invoke(["flag-bridge", "S7", "1"], llm).exit_code == 2
    assert len(ctx.store.list_bridge_flags()) == 1
