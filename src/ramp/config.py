"""config.toml loading and validation (contracts/config.toml.md). Shared leaf utility."""

import os
import tomllib
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

ROLES = ("planner", "writer", "reviewer", "grader")
PLACEHOLDER = "REPLACE_ME"
# Working defaults so a first `ramp init` runs without editing config.toml. The reviewer must differ from the writer.
DEFAULT_MODELS = {"planner": "claude-opus-5-5", "writer": "claude-sonnet-5-5",
                  "reviewer": "claude-haiku-5-5", "grader": "claude-haiku-5-5"}
# USD per million tokens (input, output), Anthropic list prices checked 2026-11-22. Haiku 5.5 is priced for prompts up
# to 100k tokens; the input caps keep every call below that. Prices on another provider may differ: edit them.
DEFAULT_PRICES = {"planner": (4.0, 20.0), "writer": (2.0, 10.0), "reviewer": (0.10, 0.50), "grader": (0.10, 0.50)}
_LOOPBACK = {"localhost", "127.0.0.1", "::1"}


class ConfigError(Exception):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GateConfig(_Strict):
    pass_threshold: int = Field(default=3, ge=0, le=5)
    # The reviewer defaults to a different model than the writer (manifest §3.3). Same model needs this opt-in.
    allow_same_reviewer_model: bool = False


class DebugConfig(_Strict):
    # Local JSONL trace of every model call under <home>/logs (prompts, replies, errors). Never leaves the machine.
    trace_llm: bool = True


class Caps(_Strict):
    max_cost_usd_per_command: float = Field(default=0.50, gt=0)
    max_cost_usd_per_day: float = Field(default=3.00, gt=0)
    max_regenerations: int = Field(default=2, ge=0)
    max_retries: int = Field(default=2, ge=0)


def _check_base_url(url: str) -> None:
    u = urlparse(url)
    if u.scheme == "https" and u.hostname:
        return
    if u.scheme == "http" and u.hostname in _LOOPBACK:
        return
    raise ValueError("base_url must be https (http only for loopback)")


class RoleConfig(_Strict):
    base_url: str
    # name of an env var holding the endpoint URL; when set and non-empty it replaces base_url at call time
    base_url_env: str = ""
    api_key_env: str = ""
    # set (e.g. "2023-12-01-preview") for an Azure-OpenAI-style endpoint: base_url is then the host only, the route is
    # /openai/deployments/<model>/chat/completions?api-version=<this> and the key goes in an `api-key` header
    api_version: str = ""
    model: str
    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    usd_per_mtok_in: float = Field(default=0.0, ge=0)
    usd_per_mtok_out: float = Field(default=0.0, ge=0)
    # false = ask the provider not to spend output tokens on hidden reasoning (native Anthropic only);
    # unset = the provider's default
    thinking: bool | None = None

    @model_validator(mode="after")
    def _check_url(self):
        _check_base_url(self.base_url)
        return self

    def resolve_base_url(self, environ: Mapping[str, str] | None = None) -> "RoleConfig":
        """This role with base_url taken from base_url_env when that variable is set (same https/loopback rule)."""
        env = os.environ if environ is None else environ
        url = env.get(self.base_url_env, "").strip() if self.base_url_env else ""
        if not url:
            return self
        try:
            _check_base_url(url)
        except ValueError as e:
            raise ConfigError(f"environment variable {self.base_url_env}: {e}") from None
        return self.model_copy(update={"base_url": url})


class Config(_Strict):
    schema_version: int = 1
    gate: GateConfig = GateConfig()
    caps: Caps = Caps()
    debug: DebugConfig = DebugConfig()
    roles: dict[str, RoleConfig]

    @model_validator(mode="after")
    def _check_roles(self):
        missing = [r for r in ROLES if r not in self.roles]
        if missing:
            raise ValueError(f"missing role(s): {', '.join(missing)}")
        extra = [r for r in self.roles if r not in ROLES]
        if extra:
            raise ValueError(f"unknown role(s): {', '.join(extra)}")
        if self.roles["reviewer"].model == self.roles["writer"].model and not self.gate.allow_same_reviewer_model:
            raise ValueError("roles.reviewer.model must differ from roles.writer.model "
                             "(or set gate.allow_same_reviewer_model = true to accept the same model)")
        return self

    def require_model(self, role: str) -> RoleConfig:
        """Return the role config, refusing placeholder models (called before any provider call)."""
        rc = self.roles[role]
        if rc.model.startswith(PLACEHOLDER):
            raise ConfigError(f"config.toml: set roles.{role}.model (still a {PLACEHOLDER} placeholder)")
        return rc


def load_config(path: Path) -> Config:
    try:
        data = tomllib.loads(Path(path).read_text())
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ConfigError(f"cannot read {path}: {e}") from e
    try:
        return Config.model_validate(data)
    except ValidationError as e:
        raise ConfigError(f"invalid {path}: {e}") from e


def default_toml() -> str:
    """Default config.toml. Contains no secrets: the API key lives in the named environment variable."""

    def role(name: str, max_in: int, max_out: int, thinking: bool | None = None) -> str:
        think = "" if thinking is None else f"thinking = {str(thinking).lower()}\n"
        return (
            'base_url = "https://openrouter.ai/api/v1"\n'
            'base_url_env = "OPENROUTER_API_URL"\n'
            'api_key_env = "API_KEY"\n'
            f'model = "{DEFAULT_MODELS[name]}"\n'
            f"max_input_tokens = {max_in}\n"
            f"max_output_tokens = {max_out}\n"
            f"usd_per_mtok_in = {DEFAULT_PRICES[name][0]}\n"
            f"usd_per_mtok_out = {DEFAULT_PRICES[name][1]}\n" + think
        )

    return (
        "# ramp configuration. The models are working defaults: change them, and check the prices (0.0 would mean the cost caps never trigger).\n"
        "# The API key is read from the environment variable named by api_key_env.\n"
        "# If the variable named by base_url_env is set, its value replaces base_url.\n"
        "schema_version = 1\n\n"
        "[gate]\npass_threshold = 3\n\n"
        "[caps]\n"
        "max_cost_usd_per_command = 0.50\nmax_cost_usd_per_day = 3.00\n"
        "max_regenerations = 2\nmax_retries = 2\n\n"
        "[debug]\n# local trace of every model call in <home>/logs (prompts, replies, errors); never leaves the machine\n"
        "trace_llm = true\n\n"
        f"[roles.planner]  # strong\n{role('planner', 24000, 12000)}\n"
        f"[roles.writer]  # strong\n{role('writer', 24000, 16000)}\n"
        f"[roles.reviewer]  # must differ from the writer\n{role('reviewer', 24000, 8000, thinking=False)}\n"
        f"[roles.grader]  # cheap\n{role('grader', 6000, 2000, thinking=False)}"
    )


def write_default(home: Path) -> Path:
    """Write the default config unless one exists; returns its path."""
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    path = home / "config.toml"
    if not path.exists():
        path.write_text(default_toml())
    return path


LAW_FILES = ("descriptors.yaml", "claims.yaml")


def bundled_law(name: str) -> Path:
    """The shipped copy of a law file: inside an installed package, else the repo's docs/spec (checkout)."""
    packaged = Path(__file__).resolve().parent / "_law" / name
    return packaged if packaged.exists() else Path(__file__).resolve().parents[2] / "docs" / "spec" / name


def seed_law(home: Path) -> list[str]:
    """Copy descriptors.yaml and claims.yaml into home when missing; an existing file is never touched."""
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in LAW_FILES:
        target = home / name
        if not target.exists():
            target.write_bytes(bundled_law(name).read_bytes())
            copied.append(name)
    return copied
