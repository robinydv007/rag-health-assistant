"""PostgreSQL updater — increments chunks_indexed and returns completion state."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def increment_chunks_indexed(
    session: AsyncSession, doc_id: str
) -> tuple[int, int | None]:
    """Atomically increment chunks_indexed and return (chunks_indexed, chunks_total).

    Returns (chunks_indexed, chunks_total) where chunks_total may be None if
    the document row has not yet been updated by the Doc Processing Service.
    """
    result = await session.execute(
        text("""
            UPDATE documents
            SET chunks_indexed = chunks_indexed + 1, updated_at = NOW()
            WHERE doc_id = :doc_id
            RETURNING chunks_indexed, chunks_total
        """),
        {"doc_id": doc_id},
    )
    row = result.fetchone()
    if row is None:
        raise ValueError(f"Document not found: doc_id={doc_id!r}")
    chunks_indexed, chunks_total = row
    logger.debug(
        "doc_id=%s chunks_indexed=%d chunks_total=%s", doc_id, chunks_indexed, chunks_total
    )
    return chunks_indexed, chunks_total
