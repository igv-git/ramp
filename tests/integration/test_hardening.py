"""T076: cost-cap aborts, interrupts, spend persistence and regeneration caps, with the real ProviderClient."""

import builders as b
import pytest
from conftest import good_config_text, write_solution
from typer.testing import CliRunner

from ramp import models as m
from ramp import paths
from ramp.cli import app
from ramp.cli.wiring import Context
from ramp.config import load_config
from ramp.loop import init_flow, today_flow
from ramp.loop import submit_flow as sf
from ramp.providers.client import ProviderClient, TransportResult
from ramp.providers.cost import CostMeter
from ramp.providers.port import CostCapExceeded, FakeLLM, ProviderFailed
from ramp.store import db as store_db
from ramp.store.ledger import StoreLedger
from ramp.store.repos import Store

runner = CliRunner()
PRICE = 100.0  # USD per million tokens: a 1000-token call costs $0.10


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "sk-test")


def write_config(home, *, per_command=0.50, per_day=3.00, regen=2):
    text = (good_config_text().replace("usd_per_mtok_in = 0.0", f"usd_per_mtok_in = {PRICE}")
            .replace("max_cost_usd_per_command = 0.50", f"max_cost_usd_per_command = {per_command}")
            .replace("max_cost_usd_per_day = 3.00", f"max_cost_usd_per_day = {per_day}")
            .replace("max_regenerations = 2", f"max_regenerations = {regen}"))
    (home / "config.toml").write_text(text)


def scripted(responses):
    """A transport that answers by output type (1000 tokens in, none out)."""
    def transport(rc, key, system, user, output_type):
        item = responses[output_type].pop(0)
        if isinstance(item, BaseException):
            raise item
        return TransportResult(output=item, tokens_in=1000, tokens_out=0)
    return transport


def real_ctx(home, responses):
    cfg = load_config(home / "config.toml")
    store = Store(store_db.connect(home / "profile.db"))
    client = ProviderClient(cfg, CostMeter(StoreLedger(store), cfg.caps), scripted(responses), sleep=lambda s: None)
    return Context(home=home, config=cfg, store=store, llm=client), client


def init_responses():
    return {m.EligibilityResult: [b.eligible()], m.PlanOutline: [b.outline(2, 30)],
            m.SliceDraft: [b.draft_for(1), b.draft_for(2)]}


INIT_ARGS = ["init", "--skill", "python", "--to", "2", "--hours", "1", "--days", "1"]


# ---- cost cap mid-command
def test_cost_cap_mid_init_reports_the_cap_keeps_spend_and_writes_no_curriculum(law_home):
    write_config(law_home, per_command=0.35)  # eligibility, plan, writer 1 = $0.30; writer 2 trips the cap
    ctx, client = real_ctx(law_home, init_responses())
    res = runner.invoke(app, INIT_ARGS, obj={"llm": client})
    assert res.exit_code == 1 and "cap" in res.output.lower() and "$0.35" in res.output
    assert ctx.store.get_spend()[1] == pytest.approx(0.4)  # the spend of the call that tripped it is kept
    assert ctx.store.list_slice_states() == [] and not paths.plan_path("python", law_home).exists()
    ctx.store.close()


def test_init_can_be_rerun_after_a_cap_abort_and_spend_accumulates(law_home):
    write_config(law_home, per_command=0.35)
    ctx, client = real_ctx(law_home, init_responses())
    assert runner.invoke(app, INIT_ARGS, obj={"llm": client}).exit_code == 1
    ctx.store.close()
    write_config(law_home, per_command=0.50)  # the owner raises the cap
    ctx, client = real_ctx(law_home, init_responses())
    res = runner.invoke(app, INIT_ARGS, obj={"llm": client})
    assert res.exit_code == 0, res.output
    assert paths.plan_path("python", law_home).exists() and len(ctx.store.list_slice_states()) == 2
    assert ctx.store.get_spend()[1] == pytest.approx(0.8)
    ctx.store.close()


def test_cost_cap_mid_submit_blocks_the_attempt_with_the_cap_as_cause(curriculum):
    ctx0, _ = curriculum
    home = ctx0.home
    write_config(home, per_command=0.05)  # one $0.10 review call trips it
    write_solution(home)
    ctx, client = real_ctx(home, {m.ReviewerOutput: [b.review_out(rating=4)]})
    res = runner.invoke(app, ["submit"], obj={"llm": client})
    assert res.exit_code == 1 and "cap" in " ".join(res.output.split()).lower()
    row = ctx.store.list_attempts("S1")[0]
    assert row["status"] == "blocked" and row["passed"] is None and "cap" in row["blocked_cause"]
    assert ctx.store.get_spend()[1] == pytest.approx(0.1)
    assert ctx.store.get_slice_state("S1")["status"] == "current"
    ctx.store.close()


def test_spend_survives_across_commands_and_the_day_cap_stops_the_third(law_home):
    write_config(law_home, per_command=0.50, per_day=0.25)
    calls = []

    def counting(rc, key, system, user, output_type):
        calls.append(1)
        return TransportResult(output=b.grader_out(3), tokens_in=1000, tokens_out=0)

    def one_command():
        cfg = load_config(law_home / "config.toml")
        store = Store(store_db.connect(law_home / "profile.db"))
        client = ProviderClient(cfg, CostMeter(StoreLedger(store), cfg.caps), counting, sleep=lambda s: None)
        return store, client

    for expected in (0.1, 0.2):  # each command has a fresh meter; the day total comes from the database
        store, client = one_command()
        client.complete("grader", "s", "u", m.GraderOutput)
        assert store.get_spend()[1] == pytest.approx(expected)
        store.close()
    store, client = one_command()
    with pytest.raises(CostCapExceeded, match="day"):
        client.complete("grader", "s", "u", m.GraderOutput)  # 0.2 + 0.1 passes the $0.25 day cap
    with pytest.raises(CostCapExceeded, match="day"):
        client.complete("grader", "s", "u", m.GraderOutput)  # refused before any call
    assert len(calls) == 3
    store.close()


def test_a_cost_cap_while_grading_a_teachback_still_stores_it_and_unlocks(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    out = sf.run_submit(ctx)
    llm.responses["grader"] = [CostCapExceeded("per-command cost cap $0.50 reached")]
    tb = sf.complete_teachback(ctx, out, "my explanation")
    assert tb.grade is None and tb.unlocked == "S2"
    assert ctx.store.get_teachback(out.attempt_id)["answer"] == "my explanation"


# ---- Ctrl-C
def interrupted_row(ctx):
    rows = ctx.store.list_attempts("S1")
    assert len(rows) == 1
    return rows[0]


def test_interrupt_during_the_review_records_the_attempt_as_blocked_interrupted(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [KeyboardInterrupt()]
    with pytest.raises(KeyboardInterrupt):
        sf.run_submit(ctx)
    row = interrupted_row(ctx)
    assert row["status"] == "blocked" and row["blocked_cause"] == "interrupted" and row["passed"] is None
    assert "[result: green]" in row["test_output"]  # the finished test run is kept
    assert ctx.store.pending_attempts() == []
    assert ctx.store.get_slice_state("S1")["status"] == "current" and ctx.store.get_slice_state("S2")["status"] == "locked"


def test_interrupt_while_the_tests_run_records_a_blocked_attempt_too(curriculum, monkeypatch):
    ctx, llm = curriculum
    write_solution(ctx.home)

    def boom(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(sf.rexec, "run_argv", boom)
    with pytest.raises(KeyboardInterrupt):
        sf.run_submit(ctx)
    row = interrupted_row(ctx)
    assert row["status"] == "blocked" and row["blocked_cause"] == "interrupted" and row["test_output"] == ""
    assert llm.calls == []


def test_the_database_stays_usable_and_the_next_submit_works_after_an_interrupt(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [KeyboardInterrupt()]
    with pytest.raises(KeyboardInterrupt):
        sf.run_submit(ctx)
    llm.calls.clear()
    assert today_flow.run_today(ctx).drained == [] and llm.calls == []  # a blocked attempt is never drained
    llm.responses["reviewer"] = [b.review_out(rating=4)]
    out = sf.run_submit(ctx)
    assert out.passed and [r["status"] for r in ctx.store.list_attempts("S1")] == ["blocked", "reviewed"]


def test_cli_interrupt_says_so_exits_1_and_still_exports(curriculum):
    ctx, llm = curriculum
    write_solution(ctx.home)
    llm.responses["reviewer"] = [KeyboardInterrupt()]
    res = runner.invoke(app, ["submit"], obj={"llm": llm})
    assert res.exit_code == 1
    text = " ".join(res.output.split())
    assert "Interrupted" in text and "ramp submit" in text
    assert '"blocked"' in (ctx.home / "exports" / "attempts.jsonl").read_text()


def test_a_started_attempt_left_by_a_hard_kill_is_blocked_by_the_drain_not_reviewed(curriculum):
    ctx, llm = curriculum
    ctx.store.add_attempt(slice_id="S1", ts="t", test_output="", diff="d", status="pending_review", fingerprint="f")
    view = today_flow.run_today(ctx)
    assert len(view.drained) == 1 and "interrupted" in view.drained[0].lower() and llm.calls == []
    row = ctx.store.get_attempt(1)
    assert row["status"] == "blocked" and row["blocked_cause"] == "interrupted"


def test_interrupt_during_init_leaves_no_curriculum_and_init_can_be_rerun(law_home):
    from ramp.cli import wiring

    llm = FakeLLM({"planner": [b.eligible(), b.outline(2, 30)], "writer": [b.draft_for(1), KeyboardInterrupt()]})
    ctx = wiring.make_context(law_home, llm=llm)
    with pytest.raises(KeyboardInterrupt):
        init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=2, hours_per_day=1.0, days=1,
                           deadline=None, goals=[])
    assert ctx.store.list_slice_states() == [] and not paths.plan_path("python", law_home).exists()
    llm = FakeLLM({"planner": [b.eligible(), b.outline(2, 30)], "writer": [b.draft_for(1), b.draft_for(2)]})
    ctx.llm = llm
    plan = init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=2, hours_per_day=1.0, days=1,
                              deadline=None, goals=[])
    assert len(plan.slices) == 2 and len(ctx.store.list_slice_states()) == 2
    ctx.store.close()


# ---- regeneration and retry caps
@pytest.mark.parametrize("regen", [0, 1, 2])
def test_reviewer_regeneration_is_capped_by_max_regenerations(curriculum, regen):
    ctx, llm = curriculum
    ctx.config = ctx.config.model_copy(update={"caps": ctx.config.caps.model_copy(update={"max_regenerations": regen})})
    write_solution(ctx.home, b.WRONG)
    bad = b.review_out(rating=1, issues=[b.CODE_ISSUE], verdict="needs_work")
    llm.responses["reviewer"] = [bad] * 5
    llm.responses["grader"] = [b.card_prompt()]
    out = sf.run_submit(ctx)
    assert len([c for c in llm.calls if c.role == "reviewer"]) == 1 + regen
    assert out.status == "reviewed" and "```" not in out.issues[0].hint  # fell back to generic text


@pytest.mark.parametrize("regen", [0, 1, 2])
def test_slice_generation_is_capped_by_max_regenerations(law_home, regen):
    from ramp.cli import wiring

    ctx = wiring.make_context(law_home, llm=FakeLLM({
        "planner": [b.eligible(), b.outline(1, 30)], "writer": [b.draft_for(1, test=b.GREEN_TEST)] * 5}))
    ctx.config = ctx.config.model_copy(update={"caps": ctx.config.caps.model_copy(update={"max_regenerations": regen})})
    with pytest.raises(init_flow.SliceGenerationError):
        init_flow.run_init(ctx, law_dir=law_home, skill="python", target_level=2, hours_per_day=1.0, days=1,
                           deadline=None, goals=[])
    assert len([c for c in ctx.llm.calls if c.role == "writer"]) == 1 + regen
    log = (paths.slice_dir(1, law_home) / "gencheck.log").read_text()
    assert log.count("RESULT fail") == 1 + regen
    ctx.store.close()


def test_provider_retries_follow_max_retries_with_backoff(law_home):
    write_config(law_home)
    cfg = load_config(law_home / "config.toml")
    cfg = cfg.model_copy(update={"caps": cfg.caps.model_copy(update={"max_retries": 3})})
    sleeps, attempts = [], []

    def failing(rc, key, system, user, output_type):
        attempts.append(1)
        raise RuntimeError("boom")

    store = Store(store_db.connect(law_home / "profile.db"))
    client = ProviderClient(cfg, CostMeter(StoreLedger(store), cfg.caps), failing, sleep=sleeps.append)
    with pytest.raises(ProviderFailed, match="4 attempt"):
        client.complete("grader", "s", "u", m.GraderOutput)
    assert len(attempts) == 4 and sleeps == [1.0, 3.0, 3.0]
    store.close()
