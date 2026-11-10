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
