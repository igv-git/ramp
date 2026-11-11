import pytest
from pydantic import BaseModel

from ramp import config
from ramp.cli import wiring
from ramp.providers.port import FakeLLM, ProviderFailed
from ramp.store import db as store_db
from ramp.store.ledger import StoreLedger
from ramp.store.repos import Store


class Out(BaseModel):
    x: int


@pytest.fixture
def store(tmp_home):
    s = Store(store_db.connect(tmp_home / "profile.db"))
    yield s
    s.close()


def good_config_text():
    return config.default_toml().replace("REPLACE_ME_DIFFERENT", "rev-model").replace(
        "REPLACE_ME_CHEAP", "cheap-model").replace('model = "REPLACE_ME"', 'model = "strong-model"')


def test_ledger_roundtrip_and_day_reset(store):
    led = StoreLedger(store)
    assert led.get() == ("", 0.0)
    led.set("2026-11-10", 1.5)
    assert led.get() == ("2026-11-10", 1.5)
    # persisted in meta, visible to a second ledger over the same store
    assert StoreLedger(store).get() == ("2026-11-10", 1.5)
    led.set("2026-11-11", 0.1)
    assert led.get() == ("2026-11-11", 0.1)


def test_make_context_builds_without_network(tmp_home, monkeypatch):
    (tmp_home / "config.toml").write_text(good_config_text())
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    ctx = wiring.make_context(tmp_home)
    try:
        assert ctx.config.gate.pass_threshold == 3
        assert ctx.store is not None and ctx.llm is not None
        assert (tmp_home / "profile.db").exists()
    finally:
        ctx.store.close()


def test_missing_key_error_names_variable_and_role(tmp_home, monkeypatch):
    (tmp_home / "config.toml").write_text(good_config_text())
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    ctx = wiring.make_context(tmp_home)
    try:
        with pytest.raises(ProviderFailed, match=r"OPENROUTER_API_KEY"):
            ctx.llm.complete("planner", "s", "u", Out)
    finally:
        ctx.store.close()


def test_placeholder_config_fails_at_use_not_at_build(tmp_home, monkeypatch):
    (tmp_home / "config.toml").write_text(config.default_toml())
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    ctx = wiring.make_context(tmp_home)
    try:
        with pytest.raises(config.ConfigError, match="roles.planner.model"):
            ctx.llm.complete("planner", "s", "u", Out)
    finally:
        ctx.store.close()


def test_missing_config_gives_actionable_error(tmp_home):
    with pytest.raises(config.ConfigError, match="ramp init"):
        wiring.make_context(tmp_home)


def test_tests_can_override_with_fake(tmp_home):
    (tmp_home / "config.toml").write_text(good_config_text())
    fake = FakeLLM({"planner": [Out(x=3)]})
    ctx = wiring.make_context(tmp_home, llm=fake)
    try:
        assert ctx.llm is fake
        assert ctx.llm.complete("planner", "s", "u", Out).x == 3
    finally:
        ctx.store.close()
