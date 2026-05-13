"""Unit tests for mock LLM and mock embedding providers (ENH-007).

These tests verify that EMBEDDING_PROVIDER=mock and LLM_PRIMARY=mock work
correctly end-to-end without any API key or network access.
"""

import pytest

from shared.clients.embedding_client import MockEmbeddingClient, get_embedding_client
from shared.clients.llm_client import stream_completion


@pytest.mark.asyncio
async def test_mock_llm_streams_canned_response(monkeypatch):
    """LLM_PRIMARY=mock yields a clearly-labelled multi-token canned response."""
    monkeypatch.setenv("LLM_PRIMARY", "mock")
    monkeypatch.setenv("LLM_FALLBACK", "mock")

    tokens: list[str] = []
    async for token in stream_completion(
        system_prompt="You are a healthcare assistant.",
        user_prompt="What is the standard aspirin dose?",
    ):
        tokens.append(token)

    full_response = "".join(tokens)
    assert len(tokens) > 1, "Mock should stream multiple tokens"
    assert "[LOCAL DEV" in full_response
    assert "no api key" in full_response.lower()


def test_get_embedding_client_returns_mock(monkeypatch):
    """get_embedding_client() returns MockEmbeddingClient when EMBEDDING_PROVIDER=mock."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    client = get_embedding_client()
    assert isinstance(client, MockEmbeddingClient)


def test_get_embedding_client_raises_on_unknown_provider(monkeypatch):
    """get_embedding_client() raises ValueError for unrecognised provider names."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "unknown_provider_xyz")
    with pytest.raises(ValueError, match="unknown_provider_xyz"):
        get_embedding_client()


@pytest.mark.asyncio
async def test_mock_embedding_and_llm_both_work_together(monkeypatch):
    """Both mock providers can be activated simultaneously with no API keys."""
    monkeypatch.setenv("EMBEDDING_PROVIDER", "mock")
    monkeypatch.setenv("LLM_PRIMARY", "mock")
    monkeypatch.setenv("LLM_FALLBACK", "mock")

    client = get_embedding_client()
    assert isinstance(client, MockEmbeddingClient)

    vectors = await client.embed(["Warfarin dosing requires INR monitoring."])
    assert len(vectors) == 1
    assert len(vectors[0]) == 3072

    tokens: list[str] = []
    async for token in stream_completion("sys", "user"):
        tokens.append(token)
    assert tokens
