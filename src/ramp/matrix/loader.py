"""Law loader: frozen descriptors and non-authoritative claims. Read-only in R2.

The earned-level writer is parked with the level exam (OD-15): nothing here records a level.
"""

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class LawError(Exception):
    pass


def _read_yaml(path: Path):
    try:
        data = yaml.safe_load(path.read_text())
    except OSError as e:
        raise LawError(f"cannot read {path}: {e}") from e
    except yaml.YAMLError as e:
        raise LawError(f"{path} is not valid YAML: {e}") from e
    return data if data is not None else {}


@dataclass(frozen=True)
class Descriptors:
    path: Path
    status: str
    _data: dict = field(repr=False)

    def skills(self) -> list[str]:
        return sorted(self._data)

    def has_skill(self, skill: str) -> bool:
        return skill in self._data

    def levels(self, skill: str) -> dict[int, str]:
        if skill not in self._data:
            raise LawError(f"no descriptors for skill {skill!r} in {self.path}")
        return dict(self._data[skill])

    def level_text(self, skill: str, level: int) -> str:
        levels = self.levels(skill)
        if level not in levels:
            raise LawError(f"no descriptor for {skill} level {level} in {self.path}")
        return levels[level]


def load_descriptors(home: Path) -> Descriptors:
    path = Path(home) / "descriptors.yaml"
    if not path.exists():
        raise LawError(f"{path} not found; copy docs/spec/descriptors.yaml there")
    raw = _read_yaml(path)
    if not isinstance(raw, dict):
        raise LawError(f"{path} must be a mapping")
    meta = raw.get("_meta") or {}
    status = meta.get("status")
    if status is None:
        raise LawError(f"{path} has no _meta.status (expected 'approved')")
    if status != "approved":
        raise LawError(f"{path} is marked {status!r}, not approved law; the owner must approve it first")
    data = {}
    for skill, levels in raw.items():
        if skill.startswith("_"):
            continue
        if not isinstance(levels, dict):
            raise LawError(f"{path}: skill {skill!r} must map levels to text")
        data[skill] = {int(k): " ".join(str(v).split()) for k, v in levels.items()}
    return Descriptors(path=path, status=status, _data=data)


@dataclass(frozen=True)
class Claims:
    levels: dict[str, int]
    authoritative: bool = False
    label: str = "claimed levels (self-reported, bridge fuel only; not earned)"


def load_claims(home: Path) -> Claims:
    path = Path(home) / "claims.yaml"
    if not path.exists():
        return Claims(levels={})
    raw = _read_yaml(path)
    me = raw.get("me") or {}
    return Claims(levels={str(k): int(v) for k, v in me.items()})
