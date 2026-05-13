"""LLM Router circuit breaker — CLOSED/OPEN/HALF_OPEN state machine.

Thresholds (matching specs/architecture/services.md#llm-router):
  failure_threshold = 3    failures in a row → OPEN
  timeout_threshold = 5.0  seconds per primary call (enforced by llm_client)
  reset_timeout     = 60.0 seconds OPEN → probe with HALF_OPEN
"""

from __future__ import annotations

import enum
import time


class CircuitState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 3,
        timeout_threshold: float = 5.0,
        reset_timeout: float = 60.0,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.timeout_threshold = timeout_threshold
        self.reset_timeout = reset_timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0.0

    def is_available(self) -> bool:
        """Return True if the primary provider should be attempted."""
        if self.state == CircuitState.OPEN:
            if time.monotonic() - self.last_failure_time > self.reset_timeout:
                old = self.state
                self.state = CircuitState.HALF_OPEN
                _log_transition(old, self.state)
                return True
            return False
        return True

    def record_success(self) -> None:
        old = self.state
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        if old != CircuitState.CLOSED:
            _log_transition(old, self.state)

    def record_failure(self) -> None:
        self.failure_count += 1
        self.last_failure_time = time.monotonic()
        if self.failure_count >= self.failure_threshold:
            old = self.state
            self.state = CircuitState.OPEN
            if old != CircuitState.OPEN:
                _log_transition(old, self.state)


def _log_transition(old: CircuitState, new: CircuitState) -> None:
    import logging
    logging.getLogger(__name__).info(
        "Circuit breaker state: %s → %s", old.value, new.value
    )


# Module-level singleton — per-process in-memory state (Phase 3).
# Distributed state (Redis) is a Phase 5 concern.
_llm_circuit_breaker = CircuitBreaker()
