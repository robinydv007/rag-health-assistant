"""Indexing Coordinator — tracks document and indexing_jobs completion."""

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


async def maybe_complete_indexing_job(
    session: AsyncSession, doc_id: str
) -> bool:
    """Increment docs_completed for an in-progress shadow re-index job.

    Called after a shadow-targeted document reaches 'indexed' status.
    Transitions the job to 'ready_to_swap' when docs_completed == docs_total.
    Returns True if the job advanced to ready_to_swap, False otherwise.
    """
    # Only shadow documents count against indexing_jobs
    result = await session.execute(
        text("SELECT target_index FROM documents WHERE doc_id = :doc_id"),
        {"doc_id": doc_id},
    )
    row = result.fetchone()
    if row is None or row[0] != "shadow":
        return False

    # Find the active job
    job_result = await session.execute(
        text("""
            SELECT job_id, docs_total, docs_completed
            FROM indexing_jobs
            WHERE status = 'in_progress'
            ORDER BY started_at DESC
            LIMIT 1
        """)
    )
    job = job_result.fetchone()
    if job is None:
        return False

    job_id, docs_total, docs_completed = job
    new_completed = docs_completed + 1

    await session.execute(
        text("""
            UPDATE indexing_jobs
            SET docs_completed = :new_completed
            WHERE job_id = :job_id
        """),
        {"new_completed": new_completed, "job_id": str(job_id)},
    )

    if new_completed >= docs_total:
        await session.execute(
            text("""
                UPDATE indexing_jobs
                SET status = 'ready_to_swap'
                WHERE job_id = :job_id
            """),
            {"job_id": str(job_id)},
        )
        logger.info(
            "Indexing job %s ready to swap — all %d docs indexed",
            job_id, docs_total,
        )
        return True

    return False
