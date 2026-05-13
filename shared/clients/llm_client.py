"""Async LLM streaming client with provider registry and circuit breaker.

Primary and fallback providers are set via env vars:
  LLM_PRIMARY=openai      (default)
  LLM_FALLBACK=anthropic  (default)

Circuit breaker (shared.llm_router.circuit_breaker):
  - 3 consecutive failures or a 5s timeout → state OPEN → skip primary
  - After 60s → HALF_OPEN probe; success → CLOSED; failure → OPEN

Adding a new provider: implement an async generator with the signature
  async def _<name>_stream(system_prompt, user_prompt) -> AsyncIterator[str]
and register it in _PROVIDERS.
"""

from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator

from shared.llm_router.circuit_breaker import _llm_circuit_breaker

logger = logging.getLogger(__name__)


# ── Provider registry ────────────────────────────────────────────────────────
# Maps provider name → callable(system_prompt, user_prompt) -> AsyncIterator[str]

_PROVIDERS: dict[str, object] = {}  # populated below after function definitions

_TIMEOUT_SECONDS = 5.0


async def stream_completion(
    system_prompt: str,
    user_prompt: str,
) -> AsyncIterator[str]:
    """Yield tokens — primary provider first, fallback on any failure.

    Integrates the circuit breaker: if OPEN, skip primary immediately.
    A 5s timeout or any exception from primary records a failure; if the
    failure threshold is reached the breaker trips to OPEN.

    Args:
        system_prompt: Instruction context for the model.
        user_prompt: The user's question with formatted source chunks.

    Yields:
        Individual text tokens as strings.

    Raises:
        ValueError: If LLM_PRIMARY or LLM_FALLBACK names an unknown provider.
        Exception: If both primary and fallback fail.
    """
    primary = os.environ.get("LLM_PRIMARY", "openai")
    fallback = os.environ.get("LLM_FALLBACK", "anthropic")

    primary_fn = _resolve(primary)
    fallback_fn = _resolve(fallback)

    if _llm_circuit_breaker.is_available():
        try:
            async with asyncio.timeout(_TIMEOUT_SECONDS):
                async for token in primary_fn(system_prompt, user_prompt):
                    yield token
            _llm_circuit_breaker.record_success()
            return
        except (asyncio.TimeoutError, Exception) as exc:
            _llm_circuit_breaker.record_failure()
            logger.warning(
                "LLM primary '%s' failed (%s: %s), circuit state=%s, switching to fallback '%s'",
                primary,
                type(exc).__name__,
                exc,
                _llm_circuit_breaker.state.value,
                fallback,
            )
    else:
        logger.info(
            "Circuit breaker OPEN — skipping primary '%s', routing to fallback '%s'",
            primary,
            fallback,
        )

    async for token in fallback_fn(system_prompt, user_prompt):
        yield token


def _resolve(name: str):
    """Return the provider function for *name* or raise ValueError."""
    fn = _PROVIDERS.get(name)
    if fn is None:
        available = ", ".join(sorted(_PROVIDERS))
        raise ValueError(
            f"Unknown LLM provider '{name}'. Available: {available}. "
            "Register a new provider in shared/clients/llm_client.py."
        )
    return fn


# ── Provider implementations ─────────────────────────────────────────────────


async def _openai_stream(system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
    import openai

    client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    stream = await client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


async def _anthropic_stream(system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    async with client.messages.stream(
        model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


async def _mock_stream(system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
    """Local-dev mock — no network call, no API key required.

    Yields a clearly-labelled canned response as multiple tokens to exercise
    the streaming code path end-to-end. Set LLM_PRIMARY=mock to use.
    """
    for token in [
        "[LOCAL DEV — no API key] ",
        "This is a placeholder answer. ",
        "Set OPENAI_API_KEY and LLM_PRIMARY=openai in .env for real responses.",
    ]:
        yield token


# ── Register providers ───────────────────────────────────────────────────────

_PROVIDERS["openai"] = _openai_stream
_PROVIDERS["anthropic"] = _anthropic_stream
_PROVIDERS["mock"] = _mock_stream
