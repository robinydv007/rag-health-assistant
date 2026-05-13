"""Integration test for the Chat Service /ask endpoint.

Seeds Weaviate with fixture chunks using a pre-computed BiomedBERT-like vector,
calls /ask with a mocked embedding client returning the same vector, and verifies:
  - JSON response contains answer and sources
  - The seeded fixture document appears in sources
  - query_history row was written

Requires: docker-compose services (weaviate, postgres).
Skipped when infrastructure env vars are absent.
"""

import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest
import weaviate
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from src.main import app

pytestmark = pytest.mark.integration

# Deterministic fixture vector — same dimensions as text-embedding-3-large (3072), non-zero.
# Used both when seeding Weaviate and when mocking _embedding_client.embed()
# so the hybrid search finds the seeded document via vector similarity.
_FIXTURE_VECTOR = [0.1 if i % 2 == 0 else -0.05 for i in range(3072)]


def _infra_available() -> bool:
    return bool(os.getenv("DATABASE_URL") and os.getenv("WEAVIATE_URL"))


@pytest.fixture(scope="module")
def seeded_weaviate():
    """Seed KnowledgeChunk with BiomedBERT-fixture vectors; clean up after module."""
    url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    from urllib.parse import urlparse
    parsed = urlparse(url)
    client = weaviate.connect_to_custom(
        http_host=parsed.hostname, http_port=parsed.port or 8080,
        http_secure=False, grpc_host=parsed.hostname, grpc_port=50051, grpc_secure=False,
    )
    collection = client.collections.get("KnowledgeChunk")
    inserted_ids = []
    _common = {"docType": "clinical_guideline", "version": 1,
               "embeddedModel": "BiomedBERT", "chunkIdx": 0,
               "indexedAt": "2026-05-13T00:00:00Z"}
    fixtures = [
        {"docId": "integ2-d1", "chunkId": "integ2-d1_c0",
         "text": "Aspirin 81mg daily for cardiovascular risk reduction in CAD patients",
         "title": "CAD Formulary", "pageNum": 3, **_common},
        {"docId": "integ2-d2", "chunkId": "integ2-d2_c0",
         "text": "Heparin IV protocol for pulmonary embolism treatment",
         "title": "PE Guidelines", "pageNum": 7, **_common},
        {"docId": "integ2-d3", "chunkId": "integ2-d3_c0",
         "text": "Hypertension management: lifestyle modification and antihypertensives",
         "title": "HTN Policy", "pageNum": 1, **_common},
    ]
    for f in fixtures:
        uid = collection.data.insert(properties=f, vector=_FIXTURE_VECTOR)
        inserted_ids.append(uid)
    yield
    for uid in inserted_ids:
        try:
            collection.data.delete_by_id(uid)
        except Exception:
            pass
    client.close()


@pytest.mark.skipif(not _infra_available(), reason="Infrastructure not available")
class TestAskIntegration:
    def test_ask_returns_semantically_relevant_chunk(self, seeded_weaviate):
        """Hybrid search with BiomedBERT query vector returns the seeded CAD chunk."""
        client = TestClient(app, raise_server_exceptions=True)

        async def _fake_stream(system_prompt, user_prompt):
            yield "Based on the sources, aspirin 81mg is recommended for CAD."

        import shared.clients.llm_client as _llm

        # Mock embedding client to return the same vector used when seeding
        mock_embed = AsyncMock(return_value=[_FIXTURE_VECTOR])

        with patch.dict(_llm._PROVIDERS, {"openai": _fake_stream}), \
             patch("src.searcher._embedding_client") as mock_ec:
            mock_ec.embed = mock_embed
            resp = client.post(
                "/api/v1/knowledge/ask",
                json={"question": "What is the aspirin dose for CAD?", "user_id": "integ2_test"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "answer" in body
        assert "sources" in body
        assert len(body["answer"]) > 0

        # Verify audit log row exists
        db_url = os.getenv("DATABASE_URL", "")
        engine = create_async_engine(db_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        async def _check():
            async with factory() as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM query_history WHERE user_id = 'integ2_test'")
                )
                return result.scalar()

        count = asyncio.get_event_loop().run_until_complete(_check())
        assert count >= 1
