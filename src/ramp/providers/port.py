"""The LLM seam: protocol, errors and a scripted fake. No network here."""

from dataclasses import dataclass
from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class ProviderError(Exception):
    pass


class ProviderOffline(ProviderError):
    """No route to the provider (connect/DNS failure). Reviews queue as pending_review."""


class ProviderFailed(ProviderError):
    """The provider failed after the retry limit, or a cap/config problem blocked the call."""


class CostCapExceeded(ProviderError):
    pass


class LLMPort(Protocol):
    def complete(self, role: str, system: str, user: str, output_type: type[T]) -> T: ...


class SpendLedger(Protocol):
    """Persistence for the daily spend counter; implemented by the store side."""

    def get(self) -> tuple[str, float]: ...

    def set(self, day: str, usd: float) -> None: ...


@dataclass
class Call:
    role: str
    system: str
    user: str
    output_type: type


class FakeLLM:
    """Scripted responses per role; an Exception in the script is raised."""

    def __init__(self, responses: dict[str, list] | None = None):
        self.responses = {k: list(v) for k, v in (responses or {}).items()}
        self.calls: list[Call] = []

    def complete(self, role, system, user, output_type):
        self.calls.append(Call(role, system, user, output_type))
        queue = self.responses.get(role)
        if not queue:
            raise AssertionError(f"FakeLLM: no scripted response left for role {role!r}")
        item = queue.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item
