"""Integration test for the Chat Service /ask endpoint.

Seeds Weaviate with 3 fixture chunks (zero-vector embeddings), calls /ask,
asserts SSE stream completes with done=true, and checks query_history row.

Requires: docker-compose services (weaviate, postgres).
Skipped when infrastructure env vars are absent.
"""

import asyncio
import json
import os

import pytest
import weaviate
import weaviate.classes as wvc
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.main import app

pytestmark = pytest.mark.integration

_VECTOR_DIM = 768
_ZERO_VECTOR = [0.0] * _VECTOR_DIM


def _infra_available() -> bool:
    return bool(os.getenv("DATABASE_URL") and os.getenv("WEAVIATE_URL"))


@pytest.fixture(scope="module")
def seeded_weaviate():
    """Seed Weaviate KnowledgeChunk with 3 fixture objects and yield; cleanup after."""
    url = os.getenv("WEAVIATE_URL", "http://localhost:8080")
    from urllib.parse import urlparse
    parsed = urlparse(url)
    client = weaviate.connect_to_custom(
        http_host=parsed.hostname, http_port=parsed.port or 8080,
        http_secure=False, grpc_host=parsed.hostname, grpc_port=50051, grpc_secure=False,
    )
    collection = client.collections.get("KnowledgeChunk")
    inserted_ids = []
    fixtures = [
        {"docId": "integ-d1", "chunkId": "integ-d1_c0", "text": "Aspirin 81mg for CAD", "title": "Formulary", "pageNum": 3, "docType": "other", "version": 1, "embeddedModel": "zero", "chunkIdx": 0},
        {"docId": "integ-d2", "chunkId": "integ-d2_c0", "text": "Heparin IV protocol for PE", "title": "Guidelines", "pageNum": 7, "docType": "other", "version": 1, "embeddedModel": "zero", "chunkIdx": 0},
        {"docId": "integ-d3", "chunkId": "integ-d3_c0", "text": "HTN management algorithm", "title": "Policy", "pageNum": 1, "docType": "other", "version": 1, "embeddedModel": "zero", "chunkIdx": 0},
    ]
    for f in fixtures:
        uuid = collection.data.insert(properties=f, vector=_ZERO_VECTOR)
        inserted_ids.append(uuid)
    yield
    for uid in inserted_ids:
        collection.data.delete_by_id(uid)
    client.close()


@pytest.mark.skipif(not _infra_available(), reason="Infrastructure not available")
class TestAskIntegration:
    def test_ask_streams_done_event_and_writes_audit_row(self, seeded_weaviate):
        client = TestClient(app, raise_server_exceptions=True)

        # Use LLM_MOCK=true to avoid real API calls
        import os
        os.environ["LLM_MOCK"] = "true"

        with client.stream(
            "POST",
            "/api/v1/knowledge/ask",
            json={"question": "What is the aspirin dose for CAD?", "user_id": "integ_test"},
        ) as resp:
            assert resp.status_code == 200
            events = []
            for line in resp.iter_lines():
                if line.startswith("data:"):
                    events.append(json.loads(line[len("data:"):].strip()))

        assert events, "No SSE events received"
        final = events[-1]
        assert final.get("done") is True

        # Verify audit log row
        db_url = os.getenv("DATABASE_URL", "")
        engine = create_async_engine(db_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)

        async def _check():
            async with factory() as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM query_history WHERE user_id = 'integ_test'")
                )
                return result.scalar()

        count = asyncio.get_event_loop().run_until_complete(_check())
        assert count >= 1
