"""Batch accumulator for embedding requests.

Accumulates (chunk_id, text) pairs and flushes to the embedding client when
BATCH_SIZE is reached or FLUSH_INTERVAL seconds have elapsed since the last flush.
"""

from __future__ import annotations

import time
import logging
from collections.abc import Callable, Awaitable

logger = logging.getLogger(__name__)

BATCH_SIZE = 64
FLUSH_INTERVAL = 10.0  # seconds


class Batcher:
    """Accumulates chunks and flushes in batches to the embedding client.

    Usage:
        batcher = Batcher(embed_fn=client.embed)
        results = await batcher.add(chunk_id, text)   # may return [] or a batch
        results = await batcher.tick()                 # time-based flush check
        remaining = await batcher.drain()             # flush whatever is buffered
    """

    def __init__(
        self,
        embed_fn: Callable[[list[str]], Awaitable[list[list[float]]]],
        flush_size: int = BATCH_SIZE,
        flush_interval: float = FLUSH_INTERVAL,
    ) -> None:
        self._embed_fn = embed_fn
        self._flush_size = flush_size
        self._flush_interval = flush_interval
        self._buf: list[tuple[str, str]] = []  # (chunk_id, text)
        self._last_flush: float = time.monotonic()

    async def add(self, chunk_id: str, text: str) -> list[tuple[str, list[float]]]:
        """Add one chunk. Returns embedded results if the size threshold is reached."""
        self._buf.append((chunk_id, text))
        if len(self._buf) >= self._flush_size:
            return await self._flush()
        return []

    async def tick(self) -> list[tuple[str, list[float]]]:
        """Time-based flush — call periodically; flushes if interval has elapsed."""
        if self._buf and (time.monotonic() - self._last_flush) >= self._flush_interval:
            return await self._flush()
        return []

    async def drain(self) -> list[tuple[str, list[float]]]:
        """Flush all buffered chunks regardless of thresholds."""
        if not self._buf:
            return []
        return await self._flush()

    async def _flush(self) -> list[tuple[str, list[float]]]:
        batch = self._buf.copy()
        self._buf.clear()
        self._last_flush = time.monotonic()
        logger.debug("Batcher flushing %d chunks", len(batch))
        chunk_ids = [cid for cid, _ in batch]
        texts = [text for _, text in batch]
        vectors = await self._embed_fn(texts)
        return list(zip(chunk_ids, vectors))
