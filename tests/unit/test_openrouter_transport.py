from pydantic import BaseModel
from pydantic_ai.models.test import TestModel

from ramp.config import RoleConfig
from ramp.providers.openrouter import OpenRouterTransport


class Out(BaseModel):
    x: int


def test_transport_returns_validated_output_and_usage_without_network():
    rc = RoleConfig(base_url="https://openrouter.ai/api/v1", api_key_env="K", model="m",
                    max_input_tokens=100, max_output_tokens=50)
    t = OpenRouterTransport(model_factory=lambda rc_, key: TestModel())
    res = t(rc, "key", "system prompt", "user text", Out)
    assert isinstance(res.output, Out)
    assert res.tokens_in > 0 and res.tokens_out > 0


def test_default_model_builds_without_network():
    from ramp.providers.openrouter import _default_model

    rc = RoleConfig(base_url="https://openrouter.ai/api/v1", api_key_env="K", model="some/model",
                    max_input_tokens=1, max_output_tokens=1)
    assert _default_model(rc, "k") is not None
    local = RoleConfig(base_url="http://localhost:11434/v1", api_key_env="", model="llama",
                       max_input_tokens=1, max_output_tokens=1)
    assert _default_model(local, "") is not None


def test_anthropic_base_url_uses_the_native_provider_without_network():
    from pydantic_ai.models.anthropic import AnthropicModel

    from ramp.providers.openrouter import _default_model

    rc = RoleConfig(base_url="https://api.anthropic.com", api_key_env="ANTHROPIC_API_KEY",
                    model="claude-haiku-5-5", max_input_tokens=1, max_output_tokens=1)
    model = _default_model(rc, "1234")
    assert isinstance(model, AnthropicModel) and model.model_name == "claude-haiku-5-5"


def test_other_hosts_are_unchanged():
    from pydantic_ai.models.openai import OpenAIChatModel

    from ramp.providers.openrouter import _default_model

    rc = RoleConfig(base_url="https://openrouter.ai/api/v1", api_key_env="K", model="openai/m",
                    max_input_tokens=1, max_output_tokens=1)
    assert isinstance(_default_model(rc, "k"), OpenAIChatModel)


def _rc(url, thinking):
    return RoleConfig(base_url=url, api_key_env="K", model="m", max_input_tokens=1, max_output_tokens=7,
                      thinking=thinking)


def test_thinking_false_disables_thinking_on_native_anthropic_only():
    from ramp.providers.openrouter import _model_settings

    assert _model_settings(_rc("https://api.anthropic.com", False)) == {
        "max_tokens": 7, "anthropic_thinking": {"type": "disabled"}}
    assert _model_settings(_rc("https://api.anthropic.com", None)) == {"max_tokens": 7}
    assert _model_settings(_rc("https://api.anthropic.com", True)) == {"max_tokens": 7}
    assert _model_settings(_rc("https://openrouter.ai/api/v1", False)) == {"max_tokens": 7}


def test_api_version_selects_the_azure_style_route_and_api_key_header():
    from openai._models import FinalRequestOptions

    from ramp.providers.openrouter import _default_model

    rc = RoleConfig(base_url="https://ai-proxy.example.com", api_version="2023-12-01-preview", api_key_env="K",
                    model="claude-haiku-5-5@default", max_input_tokens=1, max_output_tokens=1)
    client = _default_model(rc, "secret").client
    req = client._build_request(FinalRequestOptions.construct(
        method="post", url="/chat/completions", json_data={"model": rc.model, "messages": []}, headers={}))
    assert str(req.url) == ("https://ai-proxy.example.com/openai/deployments/claude-haiku-5-5@default"
                            "/chat/completions?api-version=2023-12-01-preview")
    assert req.headers["api-key"] == "secret" and "authorization" not in req.headers


def test_without_api_version_the_route_is_plain_openai_style():
    from ramp.providers.openrouter import _default_model

    rc = RoleConfig(base_url="https://gateway.example.com/v1", api_key_env="K", model="m",
                    max_input_tokens=1, max_output_tokens=1)
    assert "deployments" not in str(_default_model(rc, "k").client.base_url)
