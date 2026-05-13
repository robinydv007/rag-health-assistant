"""Unit tests for Admin Service alias swap."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from src.reindex import swap_index


@pytest.mark.asyncio
async def test_swap_index_updates_alias(mock_session, mock_weaviate):
    row = MagicMock()
    row.__getitem__ = lambda self, k: {"job_id": "job-123", "shadow_index": "KnowledgeChunk9999"}[k]
    mock_result = MagicMock()
    mock_result.mappings.return_value.fetchone.return_value = row
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch("src.reindex.asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
        mock_thread.return_value = None
        result = await swap_index(session=mock_session, weaviate_client=mock_weaviate)

    assert result["status"] == "swapped"
    assert result["swapped_to"] == "KnowledgeChunk9999"
    assert result["job_id"] == "job-123"


@pytest.mark.asyncio
async def test_swap_index_marks_job_swapped(mock_session, mock_weaviate):
    row = MagicMock()
    row.__getitem__ = lambda self, k: {"job_id": "job-123", "shadow_index": "KnowledgeChunk9999"}[k]
    mock_result = MagicMock()
    mock_result.mappings.return_value.fetchone.return_value = row

    execute_calls = []
    async def capture(query, params=None):
        execute_calls.append((str(query), params))
        return mock_result
    mock_session.execute = capture

    with patch("src.reindex.asyncio.to_thread", new_callable=AsyncMock):
        await swap_index(session=mock_session, weaviate_client=mock_weaviate)

    update_calls = [c for c in execute_calls if "status = 'swapped'" in c[0]]
    assert len(update_calls) == 1


@pytest.mark.asyncio
async def test_swap_index_raises_409_when_no_ready_job(mock_session, mock_weaviate):
    mock_result = MagicMock()
    mock_result.mappings.return_value.fetchone.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await swap_index(session=mock_session, weaviate_client=mock_weaviate)

    assert exc_info.value.status_code == 409
