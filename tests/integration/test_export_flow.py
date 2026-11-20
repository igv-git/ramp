import subprocess

import builders as b
from conftest import write_solution
from typer.testing import CliRunner

from ramp.cli import app

runner = CliRunner()


def invoke(cmd, llm, input=None):
    return runner.invoke(app, cmd, obj={"llm": llm}, input=input)


def commits(home):
    out = subprocess.run(["git", "-C", str(home), "log", "--format=%s"], check=False, capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line.startswith("ramp export")]


def test_export_writes_files_commits_and_prints_counts(curriculum):
    ctx, llm = curriculum
    res = invoke(["export"], llm)
    assert res.exit_code == 0, res.output
    assert (ctx.home / "exports" / "attempts.jsonl").exists() and (ctx.home / "exports" / "concepts.jsonl").exists()
    assert "slices completed: 0 · cards answered: 0 · bridge flags: 0 · pending reviews: 0" in " ".join(
        res.output.split())
    assert len(commits(ctx.home)) == 1
    tracked = subprocess.run(["git", "-C", str(ctx.home), "ls-files"], check=False, capture_output=True, text=True).stdout
    assert "exports/concepts.jsonl" in tracked and "profile.db" not in tracked


def test_a_second_export_with_no_change_makes_no_new_commit(curriculum):
    ctx, llm = curriculum
    invoke(["export"], llm)
    res = invoke(["export"], llm)
    assert res.exit_code == 0 and len(commits(ctx.home)) == 1


def test_today_ends_with_an_automatic_export(curriculum):
    ctx, llm = curriculum
    res = invoke(["today"], llm)
    assert res.exit_code == 0, res.output
    assert (ctx.home / "exports" / "concepts.jsonl").exists() and len(commits(ctx.home)) == 1
    assert "export failed" not in res.output


def test_submit_ends_with_an_automatic_export_that_includes_the_attempt(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home, b.WRONG)
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    llm.responses["grader"] = [b.card_prompt()]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0, res.output
    attempts = (ctx.home / "exports" / "attempts.jsonl").read_text().splitlines()
    assert len(attempts) == 1 and '"needs_work"' in attempts[0]
    assert len(commits(ctx.home)) == 1


def test_a_blocked_submit_still_exports(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home, b.WRONG)
    from ramp.providers.port import ProviderFailed

    llm.responses["reviewer"] = [ProviderFailed("down")]
    res = invoke(["submit"], llm)
    assert res.exit_code == 1
    assert '"blocked"' in (ctx.home / "exports" / "attempts.jsonl").read_text()


def test_export_failure_is_printed_and_does_not_change_today_or_submit_status(curriculum):
    ctx, llm = curriculum
    (ctx.home / "exports").write_text("in the way")
    res = invoke(["today"], llm)
    assert res.exit_code == 0 and "export failed" in res.output and "Slice 1" in res.output
    write_solution(ctx.home, b.WRONG)
    llm.responses["reviewer"] = [b.review_out(rating=1, issues=[b.CLEAN_ISSUE], verdict="needs_work")]
    llm.responses["grader"] = [b.card_prompt()]
    res = invoke(["submit"], llm)
    assert res.exit_code == 0 and "export failed" in res.output


def test_standalone_export_exits_1_on_failure(curriculum):
    ctx, llm = curriculum
    (ctx.home / "exports").write_text("in the way")
    res = invoke(["export"], llm)
    assert res.exit_code == 1 and "export failed" in res.output
