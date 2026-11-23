import pytest

from ramp import config


def test_default_toml_loads_and_every_role_has_a_usable_model(tmp_path):
    f = tmp_path / "config.toml"
    f.write_text(config.default_toml())
    cfg = config.load_config(f)
    for role in config.ROLES:
        assert cfg.require_model(role).model == config.DEFAULT_MODELS[role]  # a fresh init does not stop on models


def test_require_model_still_refuses_a_replace_me_model(tmp_path):
    f = tmp_path / "config.toml"
    f.write_text(config.default_toml().replace("claude-opus-5-5", "REPLACE_ME", 1))
    with pytest.raises(config.ConfigError, match=r"roles\.planner\.model"):
        config.load_config(f).require_model("planner")


def test_default_has_no_secret_and_names_env_var():
    text = config.default_toml()
    assert 'api_key_env = "API_KEY"' in text
    assert "sk-" not in text and "api_key =" not in text


def test_reviewer_and_writer_placeholders_differ(tmp_path):
    f = tmp_path / "config.toml"
    f.write_text(config.default_toml())
    cfg = config.load_config(f)
    assert cfg.roles["reviewer"].model != cfg.roles["writer"].model
    assert cfg.gate.pass_threshold == 3


def test_write_default_does_not_overwrite(tmp_home):
    p = config.write_default(tmp_home)
    assert p == tmp_home / "config.toml" and p.exists()
    p.write_text("# mine\n")
    config.write_default(tmp_home)
    assert p.read_text() == "# mine\n"


def test_default_config_turns_thinking_off_for_reviewer_and_grader_only():
    import tomllib

    from ramp import config

    roles = tomllib.loads(config.default_toml())["roles"]
    assert roles["reviewer"]["thinking"] is False and roles["grader"]["thinking"] is False
    assert "thinking" not in roles["planner"] and "thinking" not in roles["writer"]


def test_default_names_the_base_url_env_var_and_keeps_a_valid_fallback_url():
    text = config.default_toml()
    assert 'base_url_env = "OPENROUTER_API_URL"' in text and 'base_url = "https://openrouter.ai/api/v1"' in text


def test_default_prices_match_the_published_rates_and_make_the_caps_work(tmp_path):
    f = tmp_path / "config.toml"
    f.write_text(config.default_toml())
    cfg = config.load_config(f)
    got = {r: (cfg.roles[r].usd_per_mtok_in, cfg.roles[r].usd_per_mtok_out) for r in config.ROLES}
    assert got == {"planner": (4.0, 20.0), "writer": (2.0, 10.0), "reviewer": (0.10, 0.50), "grader": (0.10, 0.50)}
