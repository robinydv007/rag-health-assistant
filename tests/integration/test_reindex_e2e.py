"""Zero-downtime re-index end-to-end integration test.

Exercises the full flow in mock mode (no real Weaviate, SQS, or Postgres):
  Step 1 — trigger_reindex creates shadow class, inserts job, queues docs
  Step 2 — simulate indexing: maybe_complete_document + maybe_complete_indexing_job
  Step 3 — assert job status = ready_to_swap
  Step 4 — swap_index swaps alias and marks job = swapped

All dependencies are mocked; no network calls are made.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

# Functions and modules are loaded by conftest.py to avoid src namespace collision
from tests.integration.conftest import (
    admin_reindex_mod,
    maybe_complete_document,
    maybe_complete_indexing_job,
    swap_index,
    trigger_reindex,
)

# ── In-memory fake session ────────────────────────────────────────────────────


class FakeDB:
    """In-memory stand-in for AsyncSession — inspectable state instead of mocks."""

    def __init__(self, docs: list, job_id: str) -> None:
        self._docs = docs
        self._job_id = job_id
        self.job_status = "in_progress"
        self.docs_completed = 0
        self.docs_total = len(docs)

    async def execute(self, query, params=None):
        q = str(query)
        result = MagicMock()

        if "SELECT doc_id" in q and "status = 'indexed'" in q:
            result.mappings.return_value.all.return_value = self._docs

        elif "INSERT INTO indexing_jobs" in q:
            pass

        elif "SELECT target_index" in q:
            result.fetchone.return_value = ("shadow",)

        elif "indexing_jobs" in q and "status = 'in_progress'" in q:
            if self.job_status == "in_progress":
                result.fetchone.return_value = (
                    self._job_id,
                    self.docs_total,
                    self.docs_completed,
                )
            else:
                result.fetchone.return_value = None

        elif "docs_completed" in q and "SET" in q:
            self.docs_completed = params["new_completed"]

        elif "status = 'ready_to_swap'" in q and "UPDATE" in q:
            self.job_status = "ready_to_swap"

        elif "status = 'ready_to_swap'" in q and "SELECT" in q:
            if self.job_status == "ready_to_swap":
                row = MagicMock()
                _jid = self._job_id

                def _get(self_inner, k):
                    return {"job_id": _jid, "shadow_index": "KnowledgeChunkShadow"}[k]

                row.__getitem__ = _get
                result.mappings.return_value.fetchone.return_value = row
            else:
                result.mappings.return_value.fetchone.return_value = None

        elif "status = 'swapped'" in q:
            self.job_status = "swapped"

        elif "UPDATE documents" in q:
            pass

        else:
            result.fetchone.return_value = None
            result.mappings.return_value.all.return_value = []

        return result

    async def commit(self):
        pass


def _doc(doc_id: str) -> MagicMock:
    m = MagicMock()
    _data = {
        "doc_id": doc_id,
        "s3_key": f"raw/{doc_id}.pdf",
        "content_type": "application/pdf",
        "uploaded_by": "test-user",
        "title": f"Doc {doc_id}",
    }
    m.__getitem__ = lambda self, k: _data[k]
    return m


# ── Test ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_zero_downtime_reindex_end_to_end():
    """Full 4-step re-index flow passes in mock mode."""
    JOB_ID = "test-job-id"
    db = FakeDB(docs=[_doc("doc-1"), _doc("doc-2")], job_id=JOB_ID)

    sqs_messages: list[dict] = []
    mock_sqs = MagicMock()
    mock_sqs.send_message.side_effect = lambda **kw: sqs_messages.append(
        json.loads(kw["MessageBody"])
    ) or {"MessageId": "msg"}

    mock_weaviate = MagicMock()
    mock_weaviate.schema.create_class.return_value = None
    mock_weaviate.schema.get_class_shards.side_effect = Exception("not found")

    alias_updates: list[tuple[str, str]] = []

    async def mock_set_alias(client, alias, target):
        alias_updates.append((alias, target))

    mock_settings = MagicMock()
    mock_settings.shadow_index_alias = "knowledge-shadow"
    mock_settings.live_index_alias = "knowledge-live"
    mock_settings.sqs_queue_1_url = "http://sqs/queue-1"

    # ── Step 1: Trigger re-index ──────────────────────────────────────────────
    with (
        patch.object(
            admin_reindex_mod.asyncio, "to_thread",
            side_effect=lambda fn, *a, **kw: fn(*a, **kw)
        ),
        patch.object(admin_reindex_mod, "_set_alias", mock_set_alias),
        patch.object(admin_reindex_mod, "settings", mock_settings),
    ):
        result = await trigger_reindex(
            reason="e2e-test",
            session=db,
            sqs_client=mock_sqs,
            weaviate_client=mock_weaviate,
        )

    assert result["docs_queued"] == 2, f"expected 2 docs queued, got {result}"
    assert result["status"] == "in_progress"
    assert len(sqs_messages) == 2
    assert all(m["target_index"] == "shadow" for m in sqs_messages)

    # ── Step 2: Simulate indexing (both docs reach 'indexed') ─────────────────
    for doc_id in ["doc-1", "doc-2"]:
        doc_done = await maybe_complete_document(
            session=db, doc_id=doc_id, chunks_indexed=1, chunks_total=1
        )
        assert doc_done is True, f"maybe_complete_document returned False for {doc_id}"
        await maybe_complete_indexing_job(session=db, doc_id=doc_id)

    # ── Step 3: Verify job is ready_to_swap ───────────────────────────────────
    assert db.job_status == "ready_to_swap", f"expected ready_to_swap, got {db.job_status}"
    assert db.docs_completed == 2

    # ── Step 4: Swap index ────────────────────────────────────────────────────
    with (
        patch.object(
            admin_reindex_mod.asyncio, "to_thread",
            side_effect=lambda fn, *a, **kw: fn(*a, **kw)
        ),
        patch.object(admin_reindex_mod, "_set_alias", mock_set_alias),
        patch.object(admin_reindex_mod, "settings", mock_settings),
    ):
        swap_result = await swap_index(session=db, weaviate_client=mock_weaviate)

    assert swap_result["status"] == "swapped", f"expected swapped, got {swap_result}"
    assert db.job_status == "swapped"
    live_updates = [(a, t) for a, t in alias_updates if a == "knowledge-live"]
    assert len(live_updates) == 1, f"expected 1 live alias update, got {live_updates}"
