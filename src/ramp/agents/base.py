"""Shared pieces for agent functions. Agents receive an LLM port; they never import providers or store."""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLM(Protocol):
    def complete(self, role: str, system: str, user: str, output_type: type[T]) -> T: ...


def depth_label(level: int) -> str:
    """Bridge depth from a claimed level. Claims license comparison depth only (Art. II)."""
    if level >= 3:
        return "deep"
    if level == 2:
        return "moderate"
    if level == 1:
        return "shallow"
    return "none"


def depth_lines(known: dict[str, int]) -> str:
    return "\n".join(f"- {skill}: {depth_label(level)}" for skill, level in sorted(known.items()))
