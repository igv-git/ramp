import logging

import pytest
from pydantic import BaseModel
from pydantic_ai.exceptions import ModelConnectionError, ModelHTTPError, ModelTimeoutError

from ramp.config import Caps, RoleConfig
from ramp.providers.client import ProviderClient, Transport, TransportResult, classify
from ramp.providers.cost import CostMeter
from ramp.providers.port import CostCapExceeded, FakeLLM, ProviderFailed, ProviderOffline


class Out(BaseModel):
    x: int


def role(**over):
    base = {"base_url": "https://openrouter.ai/api/v1", "api_key_env": "TEST_KEY", "model": "m",
            "max_input_tokens": 100, "max_output_tokens": 50, "usd_per_mtok_in": 1.0, "usd_per_mtok_out": 2.0}
    base.update(over)
    return RoleConfig(**base)


class Cfg:
    def __init__(self, caps=None, **roles):
        self.caps = caps or Caps()
        self._roles = roles

    def require_model(self, r):
        return self._roles.get(r, role())


class Ledger:
    def __init__(self, day="", usd=0.0):
        self.v = (day, usd)

    def get(self):
        return self.v

    def set(self, day, usd):
        self.v = (day, usd)


class Clock:
    def __init__(self, day="2026-11-10"):
        self.day = day

    def __call__(self):
        return self.day


def make_client(transport, caps=None, ledger=None, sleeps=None, clock=None, **roles):
    cfg = Cfg(caps, **roles)
    meter = CostMeter(ledger or Ledger(), cfg.caps, today=clock or Clock())
    sleeps = sleeps if sleeps is not None else []
    return ProviderClient(cfg, meter, transport, sleep=sleeps.append)


def ok_transport(calls=None, tin=10, tout=5):
    def t(rc, key, system, user, output_type):
        if calls is not None:
            calls.append((rc.model, key, system, user))
        return TransportResult(output=output_type(x=1), tokens_in=tin, tokens_out=tout)
    return t


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("TEST_KEY", "sk-secret-123")


# ---- FakeLLM
def test_fake_llm_scripts_and_records():
    f = FakeLLM({"reviewer": [Out(x=7), Out(x=8)]})
    assert f.complete("reviewer", "sys", "usr", Out).x == 7
    assert f.complete("reviewer", "sys2", "usr2", Out).x == 8
    assert [c.role for c in f.calls] == ["reviewer", "reviewer"]
    assert f.calls[0].system == "sys" and f.calls[1].user == "usr2"
    assert f.calls[0].output_type is Out


def test_fake_llm_raises_scripted_errors_and_when_empty():
    f = FakeLLM({"grader": [ProviderOffline("down")]})
    with pytest.raises(ProviderOffline):
        f.complete("grader", "s", "u", Out)
    with pytest.raises(AssertionError):
        f.complete("grader", "s", "u", Out)


# ---- classification
def test_classify():
    assert classify(ModelConnectionError("m", "no route")) == "offline"
    assert classify(ConnectionError("x")) == "offline"
    assert classify(ModelTimeoutError("m", "slow")) == "retry"
    assert classify(TimeoutError()) == "retry"
    assert classify(ModelHTTPError(503, "m")) == "retry"
    assert classify(ModelHTTPError(401, "m")) == "retry"
    assert classify(ValueError("boom")) == "retry"


# ---- client behaviour
def test_success_returns_output_and_uses_env_key():
    calls = []
    c = make_client(ok_transport(calls))
    assert c.complete("planner", "s", "u", Out).x == 1
    assert calls[0][1] == "sk-secret-123"


def test_connect_error_is_offline_without_retry():
    n = []

    def t(*a):
        n.append(1)
        raise ModelConnectionError("m", "dns")

    sleeps = []
    c = make_client(t, sleeps=sleeps)
    with pytest.raises(ProviderOffline):
        c.complete("planner", "s", "u", Out)
    assert len(n) == 1 and sleeps == []


def test_http_error_retries_with_backoff_then_fails():
    n = []

    def t(*a):
        n.append(1)
        raise ModelHTTPError(503, "m")

    sleeps = []
    c = make_client(t, sleeps=sleeps)
    with pytest.raises(ProviderFailed):
        c.complete("planner", "s", "u", Out)
    assert len(n) == 3 and sleeps == [1.0, 3.0]


def test_timeout_retries_then_succeeds():
    state = {"n": 0}

    def t(rc, key, system, user, output_type):
        state["n"] += 1
        if state["n"] < 2:
            raise ModelTimeoutError("m", "slow")
        return TransportResult(output_type(x=2), 1, 1)

    sleeps = []
    c = make_client(t, sleeps=sleeps)
    assert c.complete("planner", "s", "u", Out).x == 2
    assert sleeps == [1.0]


def test_max_retries_from_caps():
    n = []

    def t(*a):
        n.append(1)
        raise TimeoutError

    c = make_client(t, caps=Caps(max_retries=0))
    with pytest.raises(ProviderFailed):
        c.complete("planner", "s", "u", Out)
    assert len(n) == 1


def test_input_cap_before_any_call():
    calls = []
    c = make_client(ok_transport(calls), planner=role(max_input_tokens=10))
    with pytest.raises(ProviderFailed, match="input cap"):
        c.complete("planner", "x" * 100, "y" * 100, Out)
    assert calls == []


def test_missing_api_key_names_variable_and_role(monkeypatch):
    monkeypatch.delenv("TEST_KEY")
    calls = []
    c = make_client(ok_transport(calls))
    with pytest.raises(ProviderFailed, match=r"TEST_KEY.*planner|planner.*TEST_KEY"):
        c.complete("planner", "s", "u", Out)
    assert calls == []


def test_empty_api_key_env_means_no_key_needed(monkeypatch):
    calls = []
    c = make_client(ok_transport(calls), planner=role(api_key_env=""))
    c.complete("planner", "s", "u", Out)
    assert calls[0][1] == ""


def test_key_never_leaks_in_errors_or_logs(caplog):
    def t(rc, key, *a):
        raise RuntimeError(f"bad auth with {key}")

    c = make_client(t)
    with caplog.at_level(logging.DEBUG), pytest.raises(ProviderFailed) as ei:
        c.complete("planner", "s", "u", Out)
    assert "sk-secret-123" not in str(ei.value)
    assert "sk-secret-123" not in caplog.text
    assert "sk-secret-123" not in repr(ei.value.__cause__ or "")


# ---- cost meter
def test_cost_accumulates_and_persists():
    led = Ledger()
    c = make_client(ok_transport(tin=1_000_000, tout=500_000), ledger=led,
                    caps=Caps(max_cost_usd_per_command=10, max_cost_usd_per_day=10))
    c.complete("planner", "s", "u", Out)
    assert led.get() == ("2026-11-10", pytest.approx(2.0))  # 1M*$1 + 0.5M*$2


def test_command_cap_exceeded_after_call_and_blocks_next():
    led = Ledger()
    c = make_client(ok_transport(tin=1_000_000, tout=0), ledger=led,
                    caps=Caps(max_cost_usd_per_command=0.5, max_cost_usd_per_day=10))
    with pytest.raises(CostCapExceeded):
        c.complete("planner", "s", "u", Out)
    assert led.get()[1] == pytest.approx(1.0)  # spend is recorded even when the cap trips
    with pytest.raises(CostCapExceeded):
        c.complete("planner", "s", "u", Out)


def test_day_cap_uses_ledger_and_resets_next_day():
    led = Ledger("2026-11-10", 2.9)
    clock = Clock()
    c = make_client(ok_transport(tin=1_000_000, tout=0), ledger=led, clock=clock,
                    caps=Caps(max_cost_usd_per_command=10, max_cost_usd_per_day=3.0))
    with pytest.raises(CostCapExceeded, match="day"):
        c.complete("planner", "s", "u", Out)
    clock.day = "2026-11-11"
    c2 = make_client(ok_transport(tin=10, tout=0), ledger=led, clock=clock,
                     caps=Caps(max_cost_usd_per_command=10, max_cost_usd_per_day=3.0))
    c2.complete("planner", "s", "u", Out)
    assert led.get()[0] == "2026-11-11" and led.get()[1] < 0.01


def test_transport_protocol_exists():
    assert Transport is not None
