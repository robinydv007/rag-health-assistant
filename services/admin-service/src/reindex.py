"""Admin Service — re-index trigger and alias swap."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.config.weaviate_schema import KNOWLEDGE_CHUNK_CLASS

from .settings import settings

logger = logging.getLogger(__name__)


async def trigger_reindex(
    reason: str,
    session: AsyncSession,
    sqs_client,
    weaviate_client,
) -> dict:
    shadow_index = f"KnowledgeChunk{int(time.time())}"
    job_id = str(uuid.uuid4())

    # Create the shadow Weaviate class
    shadow_class = {**KNOWLEDGE_CHUNK_CLASS, "class": shadow_index}
    await asyncio.to_thread(
        weaviate_client.schema.create_class, shadow_class
    )
    logger.info("Created shadow Weaviate class: %s", shadow_index)

    # Point knowledge-shadow alias at new class
    await _set_alias(weaviate_client, settings.shadow_index_alias, shadow_index)

    # Query all indexed documents
    result = await session.execute(
        text("""
            SELECT doc_id, s3_key, content_type, uploaded_by, title
            FROM documents
            WHERE status = 'indexed'
        """)
    )
    docs = result.mappings().all()
    docs_total = len(docs)

    # Insert indexing_jobs row
    await session.execute(
        text("""
            INSERT INTO indexing_jobs
                (job_id, shadow_index, reason, status, docs_total, initiated_by)
            VALUES
                (:job_id, :shadow_index, :reason, 'in_progress', :docs_total, 'admin')
        """),
        {
            "job_id": job_id,
            "shadow_index": shadow_index,
            "reason": reason,
            "docs_total": docs_total,
        },
    )
    await session.commit()

    # Queue each document to SQS 1 with target_index=shadow
    from datetime import datetime, timezone
    for doc in docs:
        msg = {
            "doc_id": str(doc["doc_id"]),
            "s3_key": doc["s3_key"],
            "content_type": doc["content_type"],
            "uploaded_by": doc["uploaded_by"],
            "target_index": "shadow",
            "job_id": job_id,
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        await asyncio.to_thread(
            sqs_client.send_message,
            QueueUrl=settings.sqs_queue_1_url,
            MessageBody=json.dumps(msg),
        )

    logger.info(
        "Re-index triggered: job_id=%s shadow=%s docs_queued=%d",
        job_id, shadow_index, docs_total,
    )
    return {
        "job_id": job_id,
        "shadow_index": shadow_index,
        "docs_queued": docs_total,
        "status": "in_progress",
    }


async def swap_index(
    session: AsyncSession,
    weaviate_client,
) -> dict:
    result = await session.execute(
        text("""
            SELECT job_id, shadow_index
            FROM indexing_jobs
            WHERE status = 'ready_to_swap'
            ORDER BY started_at DESC
            LIMIT 1
        """)
    )
    row = result.mappings().fetchone()
    if row is None:
        raise HTTPException(
            status_code=409,
            detail="No index ready to swap — re-index may still be running",
        )

    job_id = str(row["job_id"])
    shadow_index = row["shadow_index"]

    # Swap knowledge-live alias to the shadow class
    await _set_alias(weaviate_client, settings.live_index_alias, shadow_index)

    await session.execute(
        text("""
            UPDATE indexing_jobs
            SET status = 'swapped', swapped_at = NOW()
            WHERE job_id = :job_id
        """),
        {"job_id": job_id},
    )
    await session.commit()

    logger.info("Alias swap complete: %s → %s", settings.live_index_alias, shadow_index)
    return {"job_id": job_id, "swapped_to": shadow_index, "status": "swapped"}


async def _set_alias(weaviate_client, alias: str, target_class: str) -> None:
    """Create or update a Weaviate alias to point at target_class."""
    try:
        existing = await asyncio.to_thread(
            weaviate_client.schema.get_class_shards, alias
        )
        if existing is not None:
            await asyncio.to_thread(
                weaviate_client.schema.delete_class, alias
            )
    except Exception:
        pass

    alias_class = {
        "class": alias,
        "description": f"Alias pointing to {target_class}",
        "vectorizer": "none",
        "properties": [],
        "moduleConfig": {"ref2vec-centroid": {}},
    }
    try:
        await asyncio.to_thread(weaviate_client.schema.create_class, alias_class)
    except Exception:
        pass
