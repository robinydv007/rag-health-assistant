"""Unit tests for the Indexing Coordinator and chunk_audit writer."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.audit_writer import write_chunk_audit
from src.coordinator import maybe_complete_document, maybe_complete_indexing_job
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


# ── Indexing job tests ───────────────────────────────────────────────────────


def _make_result(rows):
    """Helper: create a mock execute result that returns *rows* from fetchone()."""
    mock = MagicMock()
    mock.fetchone.side_effect = rows if isinstance(rows, list) else [rows]
    return mock


@pytest.mark.asyncio
async def test_indexing_job_skips_live_documents():
    """maybe_complete_indexing_job returns False for non-shadow documents."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=_make_result(("live",)))

    result = await maybe_complete_indexing_job(session, "doc-1")

    assert result is False
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_indexing_job_returns_false_when_no_active_job():
    """Returns False when no in_progress indexing_jobs row exists."""
    session = AsyncMock()
    session.execute = AsyncMock(
        side_effect=[
            _make_result(("shadow",)),
            _make_result(None),
        ]
    )

    result = await maybe_complete_indexing_job(session, "doc-1")

    assert result is False


@pytest.mark.asyncio
async def test_indexing_job_increments_docs_completed():
    """Increments docs_completed but does NOT transition if not yet complete."""
    execute_calls = []

    async def capture_execute(query, params=None):
        execute_calls.append((str(query), params))
        if "target_index" in str(query):
            r = MagicMock()
            r.fetchone.return_value = ("shadow",)
            return r
        if "indexing_jobs" in str(query) and "status = 'in_progress'" in str(query):
            r = MagicMock()
            r.fetchone.return_value = ("job-1", 5, 3)  # docs_completed=3, docs_total=5
            return r
        r = MagicMock()
        r.fetchone.return_value = None
        return r

    session = AsyncMock()
    session.execute = capture_execute

    result = await maybe_complete_indexing_job(session, "doc-1")

    assert result is False
    update_calls = [c for c in execute_calls if "docs_completed" in c[0] and "SET" in c[0]]
    assert len(update_calls) == 1
    assert update_calls[0][1]["new_completed"] == 4


@pytest.mark.asyncio
async def test_indexing_job_transitions_to_ready_to_swap_when_complete():
    """Transitions job to ready_to_swap when docs_completed reaches docs_total."""
    execute_calls = []

    async def capture_execute(query, params=None):
        execute_calls.append((str(query), params))
        if "target_index" in str(query):
            r = MagicMock()
            r.fetchone.return_value = ("shadow",)
            return r
        if "indexing_jobs" in str(query) and "status = 'in_progress'" in str(query):
            r = MagicMock()
            r.fetchone.return_value = ("job-1", 2, 1)  # one more → complete
            return r
        r = MagicMock()
        r.fetchone.return_value = None
        return r

    session = AsyncMock()
    session.execute = capture_execute

    result = await maybe_complete_indexing_job(session, "doc-1")

    assert result is True
    swap_calls = [c for c in execute_calls if "ready_to_swap" in c[0]]
    assert len(swap_calls) == 1


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
