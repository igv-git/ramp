import json
import stat

import pytest
from pydantic import BaseModel
from pydantic_ai.exceptions import ModelConnectionError, ModelHTTPError
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from test_providers import Cfg, Clock, Ledger, Out, make_client, role

from ramp.config import Caps, DebugConfig
from ramp.providers.client import ProviderClient, TransportResult
from ramp.providers.cost import CostMeter
from ramp.providers.openrouter import OpenRouterTransport
from ramp.providers.port import ProviderFailed
from ramp.providers.trace import Tracer


def lines(tracer):
    return [json.loads(x) for x in tracer.path.read_text().splitlines()]


# ---- Tracer
def test_writes_one_json_line_per_event_and_creates_the_folder(tmp_path):
    t = Tracer(tmp_path / "logs")
    t.record({"role": "writer", "ok": True})
    t.record({"role": "reviewer", "ok": False})
    rows = lines(t)
    assert [r["role"] for r in rows] == ["writer", "reviewer"]
    assert all("ts" in r for r in rows)
    assert t.path.parent == tmp_path / "logs" and t.path.name.startswith("llm-")


def test_secret_is_redacted_everywhere(tmp_path):
    t = Tracer(tmp_path / "logs")
    t.record({"user": "my key is sk-secret-123", "error": {"message": "bad sk-secret-123"},
              "nested": ["x sk-secret-123"]}, secret="sk-secret-123")
    assert "sk-secret-123" not in t.path.read_text()
    assert "***" in t.path.read_text()


def test_disabled_tracer_writes_nothing_and_has_no_path(tmp_path):
    t = Tracer(tmp_path / "logs", enabled=False)
    t.record({"x": 1})
    assert t.path is None and not (tmp_path / "logs").exists()


def test_unwritable_location_never_breaks_a_call(tmp_path):
    blocker = tmp_path / "logs"
    blocker.write_text("a file, not a folder")
    Tracer(blocker).record({"x": 1})  # must not raise


def test_non_json_values_are_stringified(tmp_path):
    t = Tracer(tmp_path / "logs")
    t.record({"obj": object(), "path": tmp_path})
    assert lines(t)


def test_trace_file_is_private(tmp_path):
    t = Tracer(tmp_path / "logs")
    t.record({"x": 1})
    assert stat.S_IMODE(t.path.stat().st_mode) & 0o077 == 0  # prompts and code: owner only


# ---- client integration
def traced_client(transport, tmp_path, **kw):
    cfg = Cfg(kw.pop("caps", None))
    meter = CostMeter(Ledger(), cfg.caps, today=Clock())
    tracer = Tracer(tmp_path / "logs")
    return ProviderClient(cfg, meter, transport, sleep=lambda s: None, tracer=tracer), tracer


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "sk-secret-123")


def test_success_is_traced_with_prompts_output_tokens_and_cost(tmp_path):
    def t(rc, key, system, user, output_type):
        return TransportResult(output_type(x=5), 1000, 500, messages=[{"kind": "request"}])

    c, tr = traced_client(t, tmp_path)
    c.complete("writer", "SYSTEM TEXT", "USER TEXT", Out)
    (row,) = lines(tr)
    assert row["ok"] is True and row["role"] == "writer" and row["model"] == "m" and row["attempt"] == 1
    assert row["system"] == "SYSTEM TEXT" and row["user"] == "USER TEXT" and row["output"] == {"x": 5}
    assert row["tokens_in"] == 1000 and row["tokens_out"] == 500 and row["cost_usd"] > 0
    assert row["messages"] == [{"kind": "request"}] and row["duration_s"] >= 0


def test_every_failed_attempt_is_traced_with_the_models_messages(tmp_path):
    def t(*a):
        e = ModelHTTPError(503, "m")
        e.ramp_trace_messages = [{"kind": "response", "parts": ["half an answer"]}]
        raise e

    c, tr = traced_client(t, tmp_path)
    with pytest.raises(ProviderFailed) as ei:
        c.complete("writer", "s", "u", Out)
    rows = lines(tr)
    assert [r["attempt"] for r in rows] == [1, 2, 3] and not any(r["ok"] for r in rows)
    assert rows[0]["error"]["type"] == "ModelHTTPError" and "503" in rows[0]["error"]["message"]
    assert rows[0]["messages"][0]["parts"] == ["half an answer"]
    assert len({r["call"] for r in rows}) == 1
    assert "ModelHTTPError" in str(ei.value) and "trace" in str(ei.value) and str(tr.path) in str(ei.value)


def test_provider_failed_message_shows_the_exception_but_never_the_key(tmp_path):
    def t(rc, key, *a):
        raise RuntimeError(f"Exceeded maximum output retries; auth was {key}")

    c, tr = traced_client(t, tmp_path)
    with pytest.raises(ProviderFailed) as ei:
        c.complete("writer", "s", "u", Out)
    assert "RuntimeError" in str(ei.value) and "Exceeded maximum output retries" in str(ei.value)
    assert "sk-secret-123" not in str(ei.value) and "sk-secret-123" not in tr.path.read_text()


def test_offline_and_precheck_refusals_are_traced(tmp_path, monkeypatch):
    def offline(*a):
        raise ModelConnectionError("m", "no route")

    c, tr = traced_client(offline, tmp_path)
    from ramp.providers.port import ProviderOffline

    with pytest.raises(ProviderOffline):
        c.complete("writer", "s", "u", Out)
    assert lines(tr)[-1]["error"]["type"] == "ModelConnectionError" and lines(tr)[-1]["ok"] is False

    c2, tr2 = traced_client(lambda *a: None, tmp_path / "other")
    c2.config._roles["writer"] = role(max_input_tokens=1)
    with pytest.raises(ProviderFailed, match="input cap"):
        c2.complete("writer", "x" * 100, "y" * 100, Out)
    row = lines(tr2)[0]
    assert row["stage"] == "precheck" and "input cap" in row["error"]["message"] and row["ok"] is False


def test_client_without_a_tracer_still_works():
    c = make_client(lambda rc, k, s, u, ot: TransportResult(ot(x=1), 1, 1))
    assert c.complete("planner", "s", "u", Out).x == 1


def test_provider_failed_message_has_no_trace_hint_when_tracing_is_off(tmp_path):
    cfg = Cfg(Caps(max_retries=0))
    c = ProviderClient(cfg, CostMeter(Ledger(), cfg.caps, today=Clock()), lambda *a: 1 / 0,
                       sleep=lambda s: None, tracer=Tracer(tmp_path / "logs", enabled=False))
    with pytest.raises(ProviderFailed) as ei:
        c.complete("writer", "s", "u", Out)
    assert "ZeroDivisionError" in str(ei.value) and "trace:" not in str(ei.value)


# ---- the real transport: capture what the model actually said
class Item(BaseModel):
    x: int


def test_transport_returns_messages_on_success():
    from pydantic_ai.models.test import TestModel

    res = OpenRouterTransport(model_factory=lambda rc, k: TestModel())(role(), "k", "sys", "usr", Item)
    assert res.messages and res.messages[0]["kind"] == "request"


def test_transport_attaches_the_conversation_to_an_output_validation_failure():
    def bad(messages, info: AgentInfo):
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args={"x": "not a number"})])

    t = OpenRouterTransport(model_factory=lambda rc, k: FunctionModel(bad))
    with pytest.raises(Exception) as ei:
        t(role(), "k", "sys", "usr", Item)
    msgs = ei.value.ramp_trace_messages
    text = json.dumps(msgs)
    assert "not a number" in text  # what the model produced
    assert "Input should be a valid integer" in text and "retried" in text  # the validation error sent back
    assert type(ei.value).__name__ == "UnexpectedModelBehavior"


def test_transport_allows_more_than_one_output_retry():
    calls = []

    def flaky(messages, info: AgentInfo):
        calls.append(1)
        args = {"x": "bad"} if len(calls) < 3 else {"x": 7}
        return ModelResponse(parts=[ToolCallPart(tool_name=info.output_tools[0].name, args=args)])

    res = OpenRouterTransport(model_factory=lambda rc, k: FunctionModel(flaky))(role(), "k", "s", "u", Item)
    assert res.output.x == 7 and len(calls) == 3


# ---- config and wiring
def test_debug_config_defaults_to_tracing_on():
    assert DebugConfig().trace_llm is True


def test_wiring_traces_into_the_home_logs_folder(law_home, monkeypatch):
    from ramp.cli import wiring

    ctx = wiring.make_context(law_home)
    try:
        assert ctx.llm.tracer.path.parent == law_home / "logs"
    finally:
        ctx.store.close()


def test_wiring_respects_the_switch(law_home):
    from ramp.cli import wiring

    text = (law_home / "config.toml").read_text().replace("trace_llm = true", "trace_llm = false")
    (law_home / "config.toml").write_text(text)
    ctx = wiring.make_context(law_home)
    try:
        assert ctx.llm.tracer.path is None
    finally:
        ctx.store.close()


def test_logs_folder_is_git_ignored_by_init_repo(tmp_path):
    from ramp.runner.git_helper import init_repo

    init_repo(tmp_path / "home")
    assert "logs/" in (tmp_path / "home" / ".gitignore").read_text().split()
