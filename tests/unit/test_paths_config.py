from pathlib import Path

import pytest

from ramp import config, paths


def valid_toml(**over) -> str:
    def role(model):
        return f"""
base_url = "https://openrouter.ai/api/v1"
api_key_env = "OPENROUTER_API_KEY"
model = "{model}"
max_input_tokens = 1000
max_output_tokens = 500
usd_per_mtok_in = 0.0
usd_per_mtok_out = 0.0
"""
    models = {"planner": "m-plan", "writer": "m-write", "reviewer": "m-review", "grader": "m-grade"}
    models.update(over.get("models", {}))
    gate = over.get("gate", "pass_threshold = 3")
    caps = over.get("caps", "max_cost_usd_per_command = 0.5\nmax_cost_usd_per_day = 3.0")
    roles = "".join(f"\n[roles.{r}]{role(m)}" for r, m in models.items() if r not in over.get("drop", ()))
    return f"schema_version = 1\n[gate]\n{gate}\n[caps]\n{caps}\n{roles}"


def load(tmp_path, text):
    f = tmp_path / "config.toml"
    f.write_text(text)
    return config.load_config(f)


def test_home_defaults_to_dot_ramp(monkeypatch):
    monkeypatch.delenv("RAMP_HOME", raising=False)
    assert paths.home() == Path.home() / ".ramp"


def test_home_env_override(tmp_home):
    assert paths.home() == tmp_home
    assert paths.db_path() == tmp_home / "profile.db"
    assert paths.exports_dir() == tmp_home / "exports"
    assert paths.slice_dir(3) == tmp_home / "slices" / "03"


def test_valid_config_loads_with_defaults(tmp_path):
    cfg = load(tmp_path, valid_toml())
    assert cfg.gate.pass_threshold == 3
    assert cfg.caps.max_regenerations == 2
    assert cfg.caps.max_retries == 2
    assert cfg.roles["reviewer"].model == "m-review"


def test_missing_role(tmp_path):
    with pytest.raises(config.ConfigError, match="grader"):
        load(tmp_path, valid_toml(drop=("grader",)))


def test_reviewer_must_differ_from_writer(tmp_path):
    with pytest.raises(config.ConfigError, match="reviewer"):
        load(tmp_path, valid_toml(models={"reviewer": "m-write"}))


@pytest.mark.parametrize("val", [-1, 6])
def test_threshold_range(tmp_path, val):
    with pytest.raises(config.ConfigError, match="pass_threshold"):
        load(tmp_path, valid_toml(gate=f"pass_threshold = {val}"))


def test_caps_must_be_positive(tmp_path):
    with pytest.raises(config.ConfigError):
        load(tmp_path, valid_toml(caps="max_cost_usd_per_command = 0\nmax_cost_usd_per_day = 3"))


def test_http_only_for_loopback(tmp_path):
    bad = valid_toml().replace("https://openrouter.ai/api/v1", "http://example.com/v1", 1)
    with pytest.raises(config.ConfigError, match="base_url"):
        load(tmp_path, bad)
    ok = valid_toml().replace("https://openrouter.ai/api/v1", "http://localhost:11434/v1", 1)
    load(tmp_path, ok)


def test_unknown_keys_rejected(tmp_path):
    with pytest.raises(config.ConfigError):
        load(tmp_path, valid_toml() + "\nsurprise = 1\n")


def test_placeholder_model_rejected_at_call_time(tmp_path):
    cfg = load(tmp_path, valid_toml(models={"planner": "REPLACE_ME"}))
    with pytest.raises(config.ConfigError, match=r"config\.toml.*roles\.planner\.model"):
        cfg.require_model("planner")
    assert cfg.require_model("writer").model == "m-write"
