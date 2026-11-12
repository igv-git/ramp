import builders as b
from conftest import write_solution
from typer.testing import CliRunner

from ramp.cli import app

runner = CliRunner()


def invoke(cmd, llm):
    return runner.invoke(app, cmd, obj={"llm": llm})


def test_today_prints_brief_bridges_and_workspace(curriculum):
    _ctx, llm = curriculum
    res = invoke(["today"], llm)
    assert res.exit_code == 0, res.output
    assert "Slice 1" in res.output and "Count the words" in res.output
    assert "java" in res.output.lower() and "workspace" in res.output.lower()


def test_submit_needs_work_prints_locate_only_hints(curriculum):
    _ctx, llm = curriculum
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0, res.output
    assert "needs" in res.output.lower() and "src/wc/__init__.py:1" in res.output
    assert "Trace what the function hands back" in " ".join(res.output.split())  # rich wraps long lines
    assert "```" not in res.output


def test_submit_pass_unlocks_next_slice(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0, res.output
    assert "pass" in res.output.lower() and "S2" in res.output


def test_submit_green_tests_but_low_rating_explains_why(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=2)]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0
    assert "counter" in res.output.lower() and "not" in res.output.lower()


def test_submit_blocked_exits_1_with_cause_and_next_step(curriculum):
    from ramp.providers.port import ProviderFailed

    _ctx, llm = curriculum
    llm.responses["reviewer"] = [ProviderFailed("provider failed for role 'reviewer'")]
    res = invoke(["submit"], llm)
    assert res.exit_code == 1
    assert "blocked" in res.output.lower() and "provider" in res.output.lower() and "submit" in res.output.lower()


def test_today_and_submit_after_the_end(curriculum):
    ctx, llm = curriculum
    ctx.store.set_slice_state("S1", "python", "passed")
    ctx.store.set_slice_state("S2", "python", "passed")
    t = invoke(["today"], llm)
    assert t.exit_code == 0 and "no level" in t.output.lower()
    s = invoke(["submit"], llm)
    assert s.exit_code == 1


def test_commands_before_init_still_say_to_run_init(tmp_home):
    for cmd in (["today"], ["submit"]):
        res = runner.invoke(app, cmd, obj={})
        assert res.exit_code == 1 and "ramp init" in res.output


def test_today_with_config_but_no_curriculum(law_home):
    res = runner.invoke(app, ["today"], obj={})
    assert res.exit_code == 1 and "ramp init" in res.output
