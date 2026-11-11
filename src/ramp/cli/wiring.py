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
        llm = ProviderClient(config, meter, OpenRouterTransport())
    return Context(home=home, config=config, store=store, llm=llm)
