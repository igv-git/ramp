"""Filesystem locations under RAMP_HOME (default ~/.ramp). Shared leaf utility: no sqlite/subprocess/network."""

import os
from pathlib import Path


def home() -> Path:
    env = os.environ.get("RAMP_HOME")
    return Path(env).expanduser() if env else Path.home() / ".ramp"


def config_path() -> Path:
    return home() / "config.toml"


def db_path() -> Path:
    return home() / "profile.db"


def exports_dir() -> Path:
    return home() / "exports"


def descriptors_path() -> Path:
    return home() / "descriptors.yaml"


def claims_path() -> Path:
    return home() / "claims.yaml"


def plan_path(skill: str) -> Path:
    return home() / "stacks" / skill / "plan.json"


def slice_dir(index: int) -> Path:
    return home() / "slices" / f"{index:02d}"
