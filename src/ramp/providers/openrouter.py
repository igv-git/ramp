"""Real transport: a Pydantic AI agent per call, OpenRouter by default. The only module using pydantic_ai models."""

import os
from collections.abc import Callable
from urllib.parse import urlparse

from ramp.providers.client import TransportResult

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

OUTPUT_RETRIES = 3


def _default_model(rc, api_key: str):
    from pydantic_ai.models.openai import OpenAIChatModel

    host = urlparse(rc.base_url).hostname or ""
    if host.endswith("anthropic.com"):  # native Anthropic API
        from pydantic_ai.models.anthropic import AnthropicModel
        from pydantic_ai.providers.anthropic import AnthropicProvider

        return AnthropicModel(rc.model, provider=AnthropicProvider(api_key=api_key))
    if host.endswith("openrouter.ai"):
        from pydantic_ai.providers.openrouter import OpenRouterProvider

        provider = OpenRouterProvider(api_key=api_key)
    else:  # any OpenAI-compatible endpoint (Ollama, LM Studio, ...): Art. VIII
        from pydantic_ai.providers.openai import OpenAIProvider

        provider = OpenAIProvider(base_url=rc.base_url, api_key=api_key or "none")
    return OpenAIChatModel(rc.model, provider=provider)


class OpenRouterTransport:
    def __init__(self, model_factory: Callable | None = None):
        self._model_factory = model_factory or _default_model

    def __call__(self, rc, api_key: str, system: str, user: str, output_type) -> TransportResult:
        from pydantic_ai import Agent, capture_run_messages
        from pydantic_ai.messages import ModelMessagesTypeAdapter

        agent = Agent(
            self._model_factory(rc, api_key),
            output_type=output_type,
            system_prompt=system,
            model_settings={"max_tokens": rc.max_output_tokens},
            retries=OUTPUT_RETRIES,  # strict output models: give the model several tries to satisfy them
        )

        def dump(messages) -> list:
            return ModelMessagesTypeAdapter.dump_python(list(messages), mode="json")

        with capture_run_messages() as captured:
            try:
                result = agent.run_sync(user)
            except Exception as e:
                e.ramp_trace_messages = dump(captured)  # what the model said, incl. validation retries
                raise
        usage = result.usage
        return TransportResult(
            output=result.output, tokens_in=usage.input_tokens or 0, tokens_out=usage.output_tokens or 0,
            messages=dump(result.all_messages()),
        )
