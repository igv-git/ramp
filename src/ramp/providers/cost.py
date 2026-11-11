"""Cost meter: per-command and per-day USD caps. Persistence is injected (providers never touch sqlite)."""

from collections.abc import Callable
from datetime import UTC, datetime

from ramp.providers.port import CostCapExceeded, SpendLedger


def _utc_day() -> str:
    return datetime.now(UTC).date().isoformat()


class CostMeter:
    def __init__(self, ledger: SpendLedger, caps, today: Callable[[], str] = _utc_day):
        self.ledger = ledger
        self.caps = caps
        self.today = today
        self.command_usd = 0.0

    def _day_total(self) -> float:
        day, usd = self.ledger.get()
        return usd if day == self.today() else 0.0

    def ensure_budget(self) -> None:
        if self.command_usd >= self.caps.max_cost_usd_per_command:
            raise CostCapExceeded(f"per-command cost cap ${self.caps.max_cost_usd_per_command:.2f} reached")
        if self._day_total() >= self.caps.max_cost_usd_per_day:
            raise CostCapExceeded(f"per-day cost cap ${self.caps.max_cost_usd_per_day:.2f} reached (day total)")

    def add(self, role_cfg, tokens_in: int, tokens_out: int) -> float:
        usd = (tokens_in * role_cfg.usd_per_mtok_in + tokens_out * role_cfg.usd_per_mtok_out) / 1_000_000
        self.command_usd += usd
        total = self._day_total() + usd
        self.ledger.set(self.today(), total)
        self.ensure_budget()
        return usd
