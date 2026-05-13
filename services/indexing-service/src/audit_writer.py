"""chunk_audit writer — one row per indexed chunk."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .weaviate_writer import EMBEDDED_MODEL


async def write_chunk_audit(
    session: AsyncSession,
    doc_id: str,
    chunk_id: str,
    index_name: str,
) -> None:
    await session.execute(
        text("""
            INSERT INTO chunk_audit (doc_id, chunk_id, index_name, embedded_model, written_at)
            VALUES (:doc_id, :chunk_id, :index_name, :embedded_model, NOW())
        """),
        {
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "index_name": index_name,
            "embedded_model": EMBEDDED_MODEL,
        },
    )
