"""Unit tests for Admin Service re-index trigger."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.reindex import trigger_reindex


def _make_doc(
    doc_id="doc-1", s3_key="raw/doc-1.pdf", content_type="application/pdf", uploaded_by="user-1"
):
    m = MagicMock()
    m.__getitem__ = lambda self, k: {
        "doc_id": doc_id, "s3_key": s3_key,
        "content_type": content_type, "uploaded_by": uploaded_by, "title": "Test Doc",
    }[k]
    return m


@pytest.mark.asyncio
async def test_trigger_reindex_creates_shadow_class(mock_session, mock_sqs, mock_weaviate):
    docs = [_make_doc("doc-1"), _make_doc("doc-2")]
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = docs
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("src.reindex.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = None
        result = await trigger_reindex(
            reason="test",
            session=mock_session,
            sqs_client=mock_sqs,
            weaviate_client=mock_weaviate,
        )

    assert result["docs_queued"] == 2
    assert result["status"] == "in_progress"
    assert result["shadow_index"].startswith("KnowledgeChunk")
    assert "job_id" in result


@pytest.mark.asyncio
async def test_trigger_reindex_inserts_indexing_jobs_row(mock_session, mock_sqs, mock_weaviate):
    docs = [_make_doc("doc-1")]
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = docs
    mock_session.execute = AsyncMock(return_value=mock_result)

    execute_calls = []
    async def capture_execute(query, params=None):
        execute_calls.append((str(query), params))
        return mock_result
    mock_session.execute = capture_execute

    with patch("src.reindex.asyncio.to_thread", new_callable=AsyncMock):
        await trigger_reindex(
            reason="audit",
            session=mock_session,
            sqs_client=mock_sqs,
            weaviate_client=mock_weaviate,
        )

    insert_calls = [c for c in execute_calls if "INSERT INTO indexing_jobs" in c[0]]
    assert len(insert_calls) == 1
    params = insert_calls[0][1]
    assert params["docs_total"] == 1
    assert params["reason"] == "audit"


@pytest.mark.asyncio
async def test_trigger_reindex_queues_sqs_messages(mock_session, mock_sqs, mock_weaviate):
    docs = [_make_doc("doc-1"), _make_doc("doc-2"), _make_doc("doc-3")]
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = docs
    mock_session.execute = AsyncMock(return_value=mock_result)

    sqs_calls = []

    async def mock_to_thread(fn, *args, **kwargs):
        if fn == mock_sqs.send_message:
            sqs_calls.append(kwargs)
        return None

    with patch("src.reindex.asyncio.to_thread", side_effect=mock_to_thread):
        result = await trigger_reindex(
            reason="test",
            session=mock_session,
            sqs_client=mock_sqs,
            weaviate_client=mock_weaviate,
        )

    assert result["docs_queued"] == 3
    assert len(sqs_calls) == 3
    for call in sqs_calls:
        import json
        body = json.loads(call["MessageBody"])
        assert body["target_index"] == "shadow"
