import builders as b
import pytest
from typer.testing import CliRunner

from ramp import config
from ramp.cli import app
from ramp.providers.port import FakeLLM

runner = CliRunner()
ARGS = ["init", "--skill", "python", "--to", "2", "--hours", "1", "--days", "1"]


@pytest.fixture
def seeded(tmp_home):
    import shutil

    from conftest import SPEC

    shutil.copy(SPEC / "descriptors.yaml", tmp_home / "descriptors.yaml")
    shutil.copy(SPEC / "claims.yaml", tmp_home / "claims.yaml")
    return tmp_home


def good_llm():
    return FakeLLM({"planner": [b.eligible(), b.outline(2, 30)], "writer": [b.draft_for(1), b.draft_for(2)]})


def finish_config(home):
    from conftest import good_config_text

    (home / "config.toml").write_text(good_config_text())


def test_init_first_run_creates_home_repo_and_default_config(seeded):
    # no config yet: init creates it, but placeholder models stop the run with an actionable message
    res = runner.invoke(app, ARGS, obj={})
    assert res.exit_code == 1
    assert (seeded / "config.toml").exists() and (seeded / ".git").is_dir()
    assert "profile.db" in (seeded / ".gitignore").read_text().split()
    assert "config.toml" in res.output and "model" in res.output
    assert not (seeded / "stacks").exists()


def test_init_success_prints_curriculum(seeded):
    config.write_default(seeded)
    finish_config(seeded)
    res = runner.invoke(app, ARGS, obj={"llm": good_llm()})
    assert res.exit_code == 0, res.output
    assert "Slice 1" in res.output and "Slice 2" in res.output
    assert "60" in res.output  # total minutes vs stated hours
    assert (seeded / ".git").is_dir()
    assert (seeded / "stacks" / "python" / "plan.json").exists()


def test_init_accepts_all_flags(seeded):
    config.write_default(seeded)
    finish_config(seeded)
    res = runner.invoke(
        app, [*ARGS, "--deadline", "2026-12-01", "--law-dir", str(seeded)], obj={"llm": good_llm()})
    assert res.exit_code == 0, res.output


def test_init_prompts_for_missing_hours(seeded):
    config.write_default(seeded)
    finish_config(seeded)
    res = runner.invoke(app, ["init", "--skill", "python", "--to", "2"], input="1\n1\n\n\n", obj={"llm": good_llm()})
    assert res.exit_code == 0, res.output


def test_init_refusal_exit_1_with_reasons(seeded):
    config.write_default(seeded)
    finish_config(seeded)
    llm = FakeLLM({"planner": [b.eligible(False, ["needs a GPU cluster"])]})
    res = runner.invoke(app, ARGS, obj={"llm": llm})
    assert res.exit_code == 1 and "needs a GPU cluster" in res.output
    assert not (seeded / "stacks").exists()


def test_init_mock_descriptors_exit_1(seeded):
    config.write_default(seeded)
    finish_config(seeded)
    d = seeded / "descriptors.yaml"
    d.write_text(d.read_text().replace("status: approved", "status: mock"))
    res = runner.invoke(app, ARGS, obj={"llm": FakeLLM({})})
    assert res.exit_code == 1 and "mock" in res.output


def test_init_generation_failure_exit_1(seeded):
    config.write_default(seeded)
    finish_config(seeded)
    bad = b.draft_for(1, test=b.GREEN_TEST)
    llm = FakeLLM({"planner": [b.eligible(), b.outline(1, 30)], "writer": [bad, bad, bad]})
    res = runner.invoke(app, ARGS, obj={"llm": llm})
    assert res.exit_code == 1 and "S1" in res.output and "green" in res.output


@pytest.mark.parametrize("cmd", [["today"], ["submit"], ["export"], ["flag-bridge", "S1", "1"]])
def test_other_commands_before_init_say_to_run_init(tmp_home, cmd):
    res = runner.invoke(app, cmd, obj={})
    assert res.exit_code == 1 and "ramp init" in res.output


def test_dispatch_table_lists_the_five_commands():
    from ramp.cli import COMMANDS

    assert set(COMMANDS) == {"init", "today", "submit", "export", "flag-bridge"}
