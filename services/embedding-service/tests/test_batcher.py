"""Unit tests for the Batcher class."""

import time
import pytest

from src.batcher import Batcher

_VECTOR = [0.1] * 768


def _make_vector(n: int) -> list[list[float]]:
    return [[float(i)] * 768 for i in range(n)]


async def _fake_embed(texts: list[str]) -> list[list[float]]:
    return _make_vector(len(texts))


@pytest.mark.asyncio
async def test_batcher_flushes_at_size_threshold():
    """Batcher flushes exactly when flush_size chunks are accumulated."""
    calls: list[list[str]] = []

    async def tracked_embed(texts: list[str]) -> list[list[float]]:
        calls.append(texts)
        return _make_vector(len(texts))

    batcher = Batcher(embed_fn=tracked_embed, flush_size=64)

    # Add 63 chunks — should not flush
    for i in range(63):
        result = await batcher.add(f"chunk_{i}", f"text {i}")
        assert result == []

    assert calls == [], "Should not have flushed before reaching 64"

    # 64th chunk triggers flush
    result = await batcher.add("chunk_63", "text 63")
    assert len(result) == 64
    assert len(calls) == 1
    assert len(calls[0]) == 64


@pytest.mark.asyncio
async def test_batcher_flush_on_interval():
    """Batcher flushes via tick() after flush_interval has elapsed."""
    called_with: list[list[str]] = []

    async def tracked_embed(texts: list[str]) -> list[list[float]]:
        called_with.append(texts)
        return _make_vector(len(texts))

    batcher = Batcher(embed_fn=tracked_embed, flush_size=64, flush_interval=0.01)

    await batcher.add("chunk_0", "text 0")
    await batcher.add("chunk_1", "text 1")

    # No flush yet (interval not elapsed)
    result = await batcher.tick()
    assert result == []

    # Wait past the interval
    time.sleep(0.05)
    result = await batcher.tick()

    assert len(result) == 2
    assert len(called_with) == 1
    assert called_with[0] == ["text 0", "text 1"]


@pytest.mark.asyncio
async def test_batcher_drain_flushes_partial():
    """drain() flushes whatever is buffered regardless of size or time."""
    batcher = Batcher(embed_fn=_fake_embed, flush_size=64)
    await batcher.add("c1", "hello")
    await batcher.add("c2", "world")
    result = await batcher.drain()
    assert len(result) == 2
    assert {r[0] for r in result} == {"c1", "c2"}


@pytest.mark.asyncio
async def test_batcher_drain_empty():
    """drain() on empty batcher returns empty list."""
    batcher = Batcher(embed_fn=_fake_embed)
    result = await batcher.drain()
    assert result == []


@pytest.mark.asyncio
async def test_batcher_maps_chunk_ids_to_vectors():
    """Batcher correctly maps each chunk_id to its corresponding vector."""
    batcher = Batcher(embed_fn=_fake_embed, flush_size=2)
    await batcher.add("a", "text a")
    result = await batcher.add("b", "text b")

    ids = [r[0] for r in result]
    assert "a" in ids
    assert "b" in ids
