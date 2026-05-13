"""Unit tests for the Indexing Coordinator and chunk_audit writer."""

from unittest.mock import AsyncMock

import pytest
from src.audit_writer import write_chunk_audit
from src.coordinator import maybe_complete_document
from src.weaviate_writer import EMBEDDED_MODEL

# ── Coordinator tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_coordinator_sets_indexed_when_complete():
    """Coordinator sets status = 'indexed' when chunks_indexed == chunks_total."""
    session = AsyncMock()
    session.execute = AsyncMock()

    result = await maybe_complete_document(
        session=session, doc_id="doc-1", chunks_indexed=5, chunks_total=5
    )

    assert result is True
    session.execute.assert_called_once()
    sql_call = session.execute.call_args
    query_str = str(sql_call.args[0])
    assert "status = 'indexed'" in query_str


@pytest.mark.asyncio
async def test_coordinator_no_update_when_incomplete():
    """Coordinator does NOT update status when chunks_indexed < chunks_total."""
    session = AsyncMock()

    result = await maybe_complete_document(
        session=session, doc_id="doc-1", chunks_indexed=3, chunks_total=5
    )

    assert result is False
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_coordinator_no_update_when_total_unknown():
    """Coordinator does NOT update status when chunks_total is None."""
    session = AsyncMock()

    result = await maybe_complete_document(
        session=session, doc_id="doc-1", chunks_indexed=1, chunks_total=None
    )

    assert result is False
    session.execute.assert_not_called()


# ── Audit writer tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_writer_inserts_with_correct_model():
    """chunk_audit writer inserts a row with embedded_model = 'text-embedding-3-large'."""
    session = AsyncMock()
    session.execute = AsyncMock()

    await write_chunk_audit(
        session=session,
        doc_id="doc-2",
        chunk_id="doc-2_chunk_0001",
        index_name="live",
    )

    session.execute.assert_called_once()
    sql_call = session.execute.call_args
    params = sql_call.args[1]
    assert params["embedded_model"] == EMBEDDED_MODEL
    assert params["doc_id"] == "doc-2"
    assert params["chunk_id"] == "doc-2_chunk_0001"
    assert params["index_name"] == "live"
