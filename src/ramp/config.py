"""config.toml loading and validation (contracts/config.toml.md). Shared leaf utility."""

import tomllib
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

ROLES = ("planner", "writer", "reviewer", "grader")
PLACEHOLDER = "REPLACE_ME"
_LOOPBACK = {"localhost", "127.0.0.1", "::1"}


class ConfigError(Exception):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GateConfig(_Strict):
    pass_threshold: int = Field(default=3, ge=0, le=5)


class Caps(_Strict):
    max_cost_usd_per_command: float = Field(default=0.50, gt=0)
    max_cost_usd_per_day: float = Field(default=3.00, gt=0)
    max_regenerations: int = Field(default=2, ge=0)
    max_retries: int = Field(default=2, ge=0)


class RoleConfig(_Strict):
    base_url: str
    api_key_env: str = ""
    model: str
    max_input_tokens: int = Field(gt=0)
    max_output_tokens: int = Field(gt=0)
    usd_per_mtok_in: float = Field(default=0.0, ge=0)
    usd_per_mtok_out: float = Field(default=0.0, ge=0)

    @model_validator(mode="after")
    def _check_url(self):
        u = urlparse(self.base_url)
        if u.scheme == "https" and u.hostname:
            return self
        if u.scheme == "http" and u.hostname in _LOOPBACK:
            return self
        raise ValueError("base_url must be https (http only for loopback)")


class Config(_Strict):
    schema_version: int = 1
    gate: GateConfig = GateConfig()
    caps: Caps = Caps()
    roles: dict[str, RoleConfig]

    @model_validator(mode="after")
    def _check_roles(self):
        missing = [r for r in ROLES if r not in self.roles]
        if missing:
            raise ValueError(f"missing role(s): {', '.join(missing)}")
        extra = [r for r in self.roles if r not in ROLES]
        if extra:
            raise ValueError(f"unknown role(s): {', '.join(extra)}")
        if self.roles["reviewer"].model == self.roles["writer"].model:
            raise ValueError("roles.reviewer.model must differ from roles.writer.model")
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

    def role(model: str, max_in: int, max_out: int) -> str:
        return (
            'base_url = "https://openrouter.ai/api/v1"\n'
            'api_key_env = "OPENROUTER_API_KEY"\n'
            f'model = "{model}"\n'
            f"max_input_tokens = {max_in}\n"
            f"max_output_tokens = {max_out}\n"
            "usd_per_mtok_in = 0.0\n"
            "usd_per_mtok_out = 0.0\n"
        )

    return (
        "# ramp configuration. Set the four `model` ids (and prices for the cost meter).\n"
        "# The API key is read from the environment variable named by api_key_env.\n"
        "schema_version = 1\n\n"
        "[gate]\npass_threshold = 3\n\n"
        "[caps]\n"
        "max_cost_usd_per_command = 0.50\nmax_cost_usd_per_day = 3.00\n"
        "max_regenerations = 2\nmax_retries = 2\n\n"
        f"[roles.planner]  # strong\n{role(PLACEHOLDER, 24000, 6000)}\n"
        f"[roles.writer]  # strong\n{role(PLACEHOLDER, 24000, 8000)}\n"
        f"[roles.reviewer]  # must differ from the writer\n{role(PLACEHOLDER + '_DIFFERENT', 24000, 3000)}\n"
        f"[roles.grader]  # cheap\n{role(PLACEHOLDER + '_CHEAP', 6000, 600)}"
    )


def write_default(home: Path) -> Path:
    """Write the default config unless one exists; returns its path."""
    home = Path(home)
    home.mkdir(parents=True, exist_ok=True)
    path = home / "config.toml"
    if not path.exists():
        path.write_text(default_toml())
    return path
