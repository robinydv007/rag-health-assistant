"""Unit tests for the /ask audit log (HC-2: always written, even on error).

Uses FastAPI TestClient with dependency overrides. LLM, Weaviate, and DB
are all mocked so no infrastructure is required.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.db import get_session
from src.main import app


def _mock_session():
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


def _session_override(session):
    async def _inner():
        yield session
    return _inner


_ASK_PAYLOAD = {"question": "What is the aspirin dose?", "user_id": "usr_001"}


class TestAuditLogOnSuccess:
    def test_audit_log_written_after_successful_ask(self):
        mock_session = _mock_session()
        app.dependency_overrides[get_session] = _session_override(mock_session)
        client = TestClient(app, raise_server_exceptions=False)

        with (
            patch("src.main.hybrid_search", new_callable=AsyncMock) as mock_search,
            patch("src.main.stream_answer") as mock_stream,
        ):
            mock_search.return_value = []

            async def _fake_stream(question, sources):
                yield 'data: {"token": "Answer.", "done": false}\n\n'
                yield 'data: {"token": "", "done": true, "sources": []}\n\n'

            mock_stream.return_value = _fake_stream("q", [])
            mock_stream.side_effect = None

            # Use side_effect with an async generator factory
            async def _gen(q, s):
                yield 'data: {"token": "Answer.", "done": false}\n\n'
                yield 'data: {"token": "", "done": true, "sources": []}\n\n'

            mock_stream.side_effect = _gen

            resp = client.post("/api/v1/knowledge/ask", json=_ASK_PAYLOAD)

        app.dependency_overrides.clear()
        # session.execute must have been called (for the audit log INSERT)
        assert mock_session.execute.await_count >= 1
        assert mock_session.commit.await_count >= 1

    def test_audit_log_written_even_when_search_fails(self):
        mock_session = _mock_session()
        app.dependency_overrides[get_session] = _session_override(mock_session)
        client = TestClient(app, raise_server_exceptions=False)

        with patch(
            "src.main.hybrid_search",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Weaviate down"),
        ):
            client.post("/api/v1/knowledge/ask", json=_ASK_PAYLOAD)

        app.dependency_overrides.clear()
        # Audit log must still be written even though search raised
        assert mock_session.execute.await_count >= 1


class TestHistoryEndpoint:
    def test_history_returns_paginated_response(self):
        mock_session = _mock_session()

        # Mock execute for both SELECT and COUNT queries
        mock_rows = MagicMock()
        mock_rows.mappings.return_value.all.return_value = []
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_session.execute = AsyncMock(side_effect=[mock_rows, mock_count])

        app.dependency_overrides[get_session] = _session_override(mock_session)
        client = TestClient(app)

        resp = client.get("/api/v1/knowledge/history?user_id=usr_001")

        app.dependency_overrides.clear()
        assert resp.status_code == 200
        body = resp.json()
        assert "queries" in body
        assert "total" in body
        assert body["total"] == 0

    def test_history_missing_user_id_returns_422(self):
        client = TestClient(app)
        resp = client.get("/api/v1/knowledge/history")
        assert resp.status_code == 422

    def test_history_limit_capped_at_100(self):
        mock_session = _mock_session()
        mock_rows = MagicMock()
        mock_rows.mappings.return_value.all.return_value = []
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0
        mock_session.execute = AsyncMock(side_effect=[mock_rows, mock_count])

        app.dependency_overrides[get_session] = _session_override(mock_session)
        client = TestClient(app)

        # limit=200 should be rejected as > 100
        resp = client.get("/api/v1/knowledge/history?user_id=u&limit=200")
        app.dependency_overrides.clear()
        assert resp.status_code == 422
