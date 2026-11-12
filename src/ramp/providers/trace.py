"""Local trace of every model call: JSON lines under ~/.ramp/logs (prompts, replies, errors, tokens, cost).

For debugging conversations with the models. It stays on this machine, is owner-readable only, is git-ignored,
and never contains the API key (the key is redacted from everything written).
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path


class Tracer:
    def __init__(self, directory: Path, enabled: bool = True):
        self.directory = Path(directory)
        self.enabled = enabled

    @property
    def path(self) -> Path | None:
        if not self.enabled:
            return None
        return self.directory / f"llm-{datetime.now(UTC).date().isoformat()}.jsonl"

    def record(self, event: dict, secret: str = "") -> None:
        """Append one event. Never raises: tracing must not break a call."""
        if not self.enabled:
            return
        try:
            row = {"ts": datetime.now(UTC).isoformat(timespec="milliseconds"), **event}
            line = json.dumps(row, ensure_ascii=False, default=str)
            if secret:
                line = line.replace(secret, "***")
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except (OSError, ValueError, TypeError):
            pass
