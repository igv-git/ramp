"""Store-backed implementation of the providers' SpendLedger protocol (structural; no providers import)."""

from ramp.store.repos import Store


class StoreLedger:
    def __init__(self, store: Store):
        self.store = store

    def get(self) -> tuple[str, float]:
        return self.store.get_spend()

    def set(self, day: str, usd: float) -> None:
        self.store.set_spend(day, usd)
