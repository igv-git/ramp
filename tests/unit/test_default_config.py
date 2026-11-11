import pytest

from ramp import config


def test_default_toml_only_fails_on_placeholder_models(tmp_path):
    f = tmp_path / "config.toml"
    f.write_text(config.default_toml())
    cfg = config.load_config(f)  # structural validation passes
    for role in config.ROLES:
        with pytest.raises(config.ConfigError, match=rf"roles\.{role}\.model"):
            cfg.require_model(role)


def test_default_has_no_secret_and_names_env_var():
    text = config.default_toml()
    assert 'api_key_env = "OPENROUTER_API_KEY"' in text
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
