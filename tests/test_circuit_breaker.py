"""Unit tests for the LLM Router circuit breaker and its integration with llm_client."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from shared.llm_router.circuit_breaker import CircuitBreaker, CircuitState

# ── CircuitBreaker state machine ─────────────────────────────────────────────


def test_initial_state_is_closed():
    cb = CircuitBreaker()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_closed_to_open_on_failure_threshold():
    cb = CircuitBreaker(failure_threshold=3)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_open_returns_unavailable():
    cb = CircuitBreaker()
    cb.state = CircuitState.OPEN
    cb.last_failure_time = 9_999_999_999.0  # far future — reset timeout not elapsed
    assert cb.is_available() is False


def test_open_transitions_to_half_open_after_reset_timeout():
    cb = CircuitBreaker(reset_timeout=60.0)
    cb.state = CircuitState.OPEN
    cb.last_failure_time = 0.0  # long ago

    with patch("shared.llm_router.circuit_breaker.time.monotonic", return_value=61.0):
        available = cb.is_available()

    assert available is True
    assert cb.state == CircuitState.HALF_OPEN


def test_half_open_success_closes_circuit():
    cb = CircuitBreaker()
    cb.state = CircuitState.HALF_OPEN
    cb.failure_count = 3
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_half_open_failure_reopens_circuit():
    cb = CircuitBreaker(failure_threshold=3)
    cb.state = CircuitState.HALF_OPEN
    cb.failure_count = 3
    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_is_available_returns_true_when_closed():
    cb = CircuitBreaker()
    assert cb.state == CircuitState.CLOSED
    assert cb.is_available() is True


# ── Integration with stream_completion ───────────────────────────────────────


@pytest.mark.asyncio
async def test_stream_completion_skips_primary_when_open():
    """When circuit is OPEN, primary provider is never called; fallback is used."""
    from shared.clients import llm_client
    from shared.llm_router.circuit_breaker import CircuitBreaker, CircuitState

    mock_primary = AsyncMock()
    mock_fallback = AsyncMock()

    async def primary_gen(*_):
        mock_primary()
        yield "primary-token"

    async def fallback_gen(*_):
        mock_fallback()
        yield "fallback-token"

    open_cb = CircuitBreaker()
    open_cb.state = CircuitState.OPEN
    open_cb.last_failure_time = 9_999_999_999.0

    with (
        patch.dict(llm_client._PROVIDERS, {"openai": primary_gen, "anthropic": fallback_gen}),
        patch("shared.clients.llm_client._llm_circuit_breaker", open_cb),
        patch.dict("os.environ", {"LLM_PRIMARY": "openai", "LLM_FALLBACK": "anthropic"}),
    ):
        tokens = [t async for t in llm_client.stream_completion("sys", "user")]

    mock_primary.assert_not_called()
    mock_fallback.assert_called_once()
    assert tokens == ["fallback-token"]


@pytest.mark.asyncio
async def test_timeout_triggers_failure():
    """A primary that hangs past 5s raises TimeoutError → record_failure called."""
    from shared.clients import llm_client

    async def hanging_gen(*_):
        await asyncio.sleep(100)
        yield "never"

    async def fallback_gen(*_):
        yield "fallback"

    fresh_cb = CircuitBreaker()

    with (
        patch.dict(llm_client._PROVIDERS, {"openai": hanging_gen, "anthropic": fallback_gen}),
        patch("shared.clients.llm_client._llm_circuit_breaker", fresh_cb),
        patch("shared.clients.llm_client._TIMEOUT_SECONDS", 0.05),
        patch.dict("os.environ", {"LLM_PRIMARY": "openai", "LLM_FALLBACK": "anthropic"}),
    ):
        tokens = [t async for t in llm_client.stream_completion("sys", "user")]

    assert fresh_cb.failure_count >= 1
    assert tokens == ["fallback"]
