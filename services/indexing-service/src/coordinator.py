"""Indexing Coordinator — sets documents.status = 'indexed' when all chunks done."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def maybe_complete_document(
    session: AsyncSession, doc_id: str, chunks_indexed: int, chunks_total: int | None
) -> bool:
    """Set status = 'indexed' if chunks_indexed == chunks_total.

    Returns True if the document was marked as indexed, False otherwise.
    """
    if chunks_total is None or chunks_indexed < chunks_total:
        return False

    await session.execute(
        text("""
            UPDATE documents
            SET status = 'indexed', updated_at = NOW()
            WHERE doc_id = :doc_id
        """),
        {"doc_id": doc_id},
    )
    logger.info(
        "Document %s fully indexed — %d chunks complete", doc_id, chunks_total
    )
    return True
