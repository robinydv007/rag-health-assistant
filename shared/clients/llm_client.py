"""Async LLM streaming client supporting OpenAI and Anthropic.

Provider is selected via LLM_PROVIDER env var ("openai" | "anthropic").
Set LLM_MOCK=true to return deterministic fixture tokens without API calls.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

_MOCK_TOKENS = [
    "Based ",
    "on ",
    "the ",
    "provided ",
    "clinical ",
    "sources, ",
    "here ",
    "is ",
    "the ",
    "answer.",
]


async def stream_completion(
    system_prompt: str,
    user_prompt: str,
    provider: str | None = None,
    mock: bool | None = None,
) -> AsyncIterator[str]:
    """Yield string tokens as they arrive from the LLM.

    Args:
        system_prompt: Instruction context for the model.
        user_prompt: The user's question with formatted source chunks.
        provider: "openai" or "anthropic". Defaults to LLM_PROVIDER env var.
        mock: Override LLM_MOCK env var. Returns fixture tokens without API call.

    Yields:
        Individual text tokens as strings.
    """
    resolved_provider = provider or os.environ.get("LLM_PROVIDER", "openai")
    resolved_mock = (
        mock if mock is not None else os.environ.get("LLM_MOCK", "false").lower() == "true"
    )

    if resolved_mock:
        async for token in _mock_stream():
            yield token
        return

    if resolved_provider == "anthropic":
        async for token in _anthropic_stream(system_prompt, user_prompt):
            yield token
    else:
        async for token in _openai_stream(system_prompt, user_prompt):
            yield token


async def _mock_stream() -> AsyncIterator[str]:
    for token in _MOCK_TOKENS:
        yield token


async def _openai_stream(system_prompt: str, user_prompt: str) -> AsyncIterator[str]:
    import openai

    client = openai.AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    stream = await client.chat.completions.create(
        model="gpt-4o",
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
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text
