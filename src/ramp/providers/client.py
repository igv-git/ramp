"""ProviderClient: caps, retries, error classification around an injected transport."""

import logging
import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel
from pydantic_ai.exceptions import ModelConnectionError, ModelTimeoutError

from ramp.providers.cost import CostMeter
from ramp.providers.port import ProviderFailed, ProviderOffline

log = logging.getLogger("ramp.providers")
BACKOFF = (1.0, 3.0)


@dataclass
class TransportResult:
    output: BaseModel
    tokens_in: int
    tokens_out: int


class Transport(Protocol):
    def __call__(self, role_cfg, api_key: str, system: str, user: str, output_type: type) -> TransportResult: ...


def classify(exc: BaseException) -> str:
    """'offline' = no route to the provider; everything else is retried."""
    if isinstance(exc, ModelTimeoutError | TimeoutError):
        return "retry"
    if isinstance(exc, ModelConnectionError | ConnectionError):
        return "offline"
    return "retry"


def _estimate_tokens(*texts: str) -> int:
    return sum(len(t) for t in texts) // 4 + 1


class ProviderClient:
    def __init__(self, config, meter: CostMeter, transport: Transport,
                 sleep: Callable[[float], None] = time.sleep):
        self.config = config
        self.meter = meter
        self.transport = transport
        self.sleep = sleep

    def complete(self, role: str, system: str, user: str, output_type):
        rc = self.config.require_model(role)
        key = ""
        if rc.api_key_env:
            key = os.environ.get(rc.api_key_env, "")
            if not key:
                raise ProviderFailed(f"role {role!r}: environment variable {rc.api_key_env} is not set")
        if _estimate_tokens(system, user) > rc.max_input_tokens:
            raise ProviderFailed(f"input cap: {role} request exceeds max_input_tokens={rc.max_input_tokens}")
        self.meter.ensure_budget()
        retries = self.config.caps.max_retries
        last: BaseException | None = None
        for attempt in range(retries + 1):
            try:
                res = self.transport(rc, key, system, user, output_type)
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt | SystemExit):
                    raise
                last = e
                if classify(e) == "offline":
                    raise ProviderOffline(f"provider unreachable for role {role!r}") from None
                log.debug("provider call failed (attempt %d): %s", attempt + 1, type(e).__name__)
                if attempt < retries:
                    self.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
                continue
            self.meter.add(rc, res.tokens_in, res.tokens_out)
            return res.output
        raise ProviderFailed(
            f"provider failed for role {role!r} after {retries + 1} attempt(s): {type(last).__name__}"
        ) from None
