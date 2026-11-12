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
