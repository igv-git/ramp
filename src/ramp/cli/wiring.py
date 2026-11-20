"""Composition root: builds config, store, spend ledger and the LLM port for a command.

Tests pass `llm=FakeLLM(...)` to replace the real provider. No network call happens here.
"""

from dataclasses import dataclass
from pathlib import Path

from ramp import paths
from ramp.config import Config, ConfigError, load_config
from ramp.providers.client import ProviderClient
from ramp.providers.cost import CostMeter
from ramp.providers.openrouter import OpenRouterTransport
from ramp.providers.port import LLMPort
from ramp.providers.trace import Tracer
from ramp.store import db as store_db
from ramp.store.ledger import StoreLedger
from ramp.store.repos import Store


@dataclass
class Context:
    home: Path
    config: Config
    store: Store
    llm: LLMPort


def make_context(home: Path | None = None, llm: LLMPort | None = None) -> Context:
    home = Path(home) if home is not None else paths.home()
    cfg_path = home / "config.toml"
    if not cfg_path.exists():
        raise ConfigError(f"{cfg_path} not found; run `ramp init` first")
    config = load_config(cfg_path)
    store = Store(store_db.connect(home / "profile.db"))
    if llm is None:
        meter = CostMeter(StoreLedger(store), config.caps)
        llm = ProviderClient(config, meter, OpenRouterTransport(),
                             tracer=Tracer(home / "logs", enabled=config.debug.trace_llm))
    return Context(home=home, config=config, store=store, llm=llm)


def context_from(typer_ctx, home: Path | None = None) -> Context:
    """Build the context for a command. Tests inject a FakeLLM through `invoke(app, ..., obj={"llm": fake})`."""
    obj = getattr(typer_ctx, "obj", None) or {}
    return make_context(home, llm=obj.get("llm"))
