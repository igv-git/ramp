"""ProviderClient: caps, retries, error classification around an injected transport."""

import logging
import os
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel
from pydantic_ai.exceptions import ModelConnectionError, ModelTimeoutError

from ramp.providers.cost import CostMeter
from ramp.providers.port import CostCapExceeded, ProviderFailed, ProviderOffline
from ramp.providers.trace import Tracer

log = logging.getLogger("ramp.providers")
BACKOFF = (1.0, 3.0)


@dataclass
class TransportResult:
    output: BaseModel
    tokens_in: int
    tokens_out: int
    messages: list | None = None  # the full exchange with the model, for the trace


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


def _detail(exc: BaseException, secret: str) -> str:
    text = f"{type(exc).__name__}: {str(exc)[:300]}".rstrip(": ")
    return text.replace(secret, "***") if secret else text


class ProviderClient:
    def __init__(self, config, meter: CostMeter, transport: Transport,
                 sleep: Callable[[float], None] = time.sleep, tracer: Tracer | None = None):
        self.config = config
        self.meter = meter
        self.transport = transport
        self.sleep = sleep
        self.tracer = tracer or Tracer(".", enabled=False)

    def _trace_hint(self) -> str:
        return f" (trace: {self.tracer.path})" if self.tracer.path else ""

    def _refuse(self, base: dict, exc: Exception, secret: str = "") -> None:
        self.tracer.record({**base, "ok": False, "stage": "precheck",
                            "error": {"type": type(exc).__name__, "message": str(exc)}}, secret)

    def complete(self, role: str, system: str, user: str, output_type):
        call = uuid.uuid4().hex[:8]
        rc = self.config.require_model(role)
        base = {"call": call, "role": role, "model": rc.model, "system": system, "user": user}
        key = ""
        if rc.api_key_env:
            key = os.environ.get(rc.api_key_env, "")
            if not key:
                err = ProviderFailed(f"role {role!r}: environment variable {rc.api_key_env} is not set")
                self._refuse(base, err)
                raise err
        if _estimate_tokens(system, user) > rc.max_input_tokens:
            err = ProviderFailed(f"input cap: {role} request exceeds max_input_tokens={rc.max_input_tokens}")
            self._refuse(base, err, key)
            raise err
        try:
            self.meter.ensure_budget()
        except CostCapExceeded as e:
            self._refuse(base, e, key)
            raise
        retries = self.config.caps.max_retries
        last: BaseException | None = None
        for attempt in range(retries + 1):
            started = time.monotonic()
            try:
                res = self.transport(rc, key, system, user, output_type)
            except BaseException as e:
                if isinstance(e, KeyboardInterrupt | SystemExit):
                    raise
                last = e
                self.tracer.record({
                    **base, "attempt": attempt + 1, "ok": False, "duration_s": round(time.monotonic() - started, 3),
                    "error": {"type": type(e).__name__, "message": str(e)},
                    "messages": getattr(e, "ramp_trace_messages", None)}, key)
                if classify(e) == "offline":
                    raise ProviderOffline(f"provider unreachable for role {role!r}") from None
                log.debug("provider call failed (attempt %d): %s", attempt + 1, type(e).__name__)
                if attempt < retries:
                    self.sleep(BACKOFF[min(attempt, len(BACKOFF) - 1)])
                continue
            cost = self.meter.add(rc, res.tokens_in, res.tokens_out)
            self.tracer.record({
                **base, "attempt": attempt + 1, "ok": True, "duration_s": round(time.monotonic() - started, 3),
                "output": res.output.model_dump(mode="json"), "tokens_in": res.tokens_in,
                "tokens_out": res.tokens_out, "cost_usd": cost, "messages": res.messages}, key)
            return res.output
        raise ProviderFailed(
            f"provider failed for role {role!r} after {retries + 1} attempt(s): {_detail(last, key)}"
            f"{self._trace_hint()}"
        ) from None
