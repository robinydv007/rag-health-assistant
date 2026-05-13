"""Unit tests for POST /api/v1/knowledge/ingest.

All external I/O (S3, PostgreSQL, SQS) is mocked so these run with no
infrastructure dependencies.
"""

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from src.db import get_session
from src.main import app

# ── helpers ──────────────────────────────────────────────────────────────────

PDF_CONTENT = b"%PDF-1.4 minimal fixture"
DOCX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
COMMON_FORM = {
    "title": "Test Clinical Guideline",
    "doc_type": "clinical_guideline",
    "uploaded_by": "user_001",
    "target_index": "live",
}


def _make_session_override():
    """Return an async generator that yields a mock AsyncSession."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    async def _override():
        yield session

    return _override, session


# ── fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def client_and_session():
    override, mock_session = _make_session_override()
    app.dependency_overrides[get_session] = override
    c = TestClient(app, raise_server_exceptions=False)
    yield c, mock_session
    app.dependency_overrides.clear()


@pytest.fixture()
def client(client_and_session):
    return client_and_session[0]


# ── tests ─────────────────────────────────────────────────────────────────────

class TestIngestHappyPath:
    def test_valid_pdf_returns_202(self, client_and_session):
        client, _ = client_and_session
        with (
            patch("src.main._s3") as mock_s3,
            patch("src.main.boto3") as mock_boto3,
        ):
            mock_s3.upload = AsyncMock()
            mock_boto3.client.return_value.send_message = MagicMock()

            resp = client.post(
                "/api/v1/knowledge/ingest",
                data=COMMON_FORM,
                files={"file": ("test.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
            )

        assert resp.status_code == 202
        body = resp.json()
        assert body["status"] == "pending"
        assert "job_id" in body
        assert "doc_id" in body
        assert "status_url" in body

    def test_valid_docx_returns_202(self, client_and_session):
        client, _ = client_and_session
        with (
            patch("src.main._s3") as mock_s3,
            patch("src.main.boto3") as mock_boto3,
        ):
            mock_s3.upload = AsyncMock()
            mock_boto3.client.return_value.send_message = MagicMock()

            resp = client.post(
                "/api/v1/knowledge/ingest",
                data=COMMON_FORM,
                files={"file": ("test.docx", io.BytesIO(b"docx content"), DOCX_CONTENT_TYPE)},
            )

        assert resp.status_code == 202

    def test_response_ids_are_uuids(self, client_and_session):
        client, _ = client_and_session
        import uuid

        with (
            patch("src.main._s3") as mock_s3,
            patch("src.main.boto3") as mock_boto3,
        ):
            mock_s3.upload = AsyncMock()
            mock_boto3.client.return_value.send_message = MagicMock()

            resp = client.post(
                "/api/v1/knowledge/ingest",
                data=COMMON_FORM,
                files={"file": ("test.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
            )

        body = resp.json()
        uuid.UUID(body["job_id"])
        uuid.UUID(body["doc_id"])


class TestIngestValidation:
    def test_unsupported_file_type_returns_422(self, client):
        resp = client.post(
            "/api/v1/knowledge/ingest",
            data=COMMON_FORM,
            files={"file": ("malware.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
        )
        assert resp.status_code == 422

    def test_missing_title_returns_422(self, client):
        resp = client.post(
            "/api/v1/knowledge/ingest",
            data={k: v for k, v in COMMON_FORM.items() if k != "title"},
            files={"file": ("test.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
        )
        assert resp.status_code == 422

    def test_missing_file_returns_422(self, client):
        resp = client.post("/api/v1/knowledge/ingest", data=COMMON_FORM)
        assert resp.status_code == 422


class TestIngestErrorPaths:
    def test_s3_failure_returns_500(self, client_and_session):
        client, _ = client_and_session
        with patch("src.main._s3") as mock_s3:
            mock_s3.upload = AsyncMock(side_effect=RuntimeError("MinIO down"))

            resp = client.post(
                "/api/v1/knowledge/ingest",
                data=COMMON_FORM,
                files={"file": ("test.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
            )

        assert resp.status_code == 500
        assert "S3" in resp.json()["detail"]

    def test_db_failure_returns_500(self, client_and_session):
        client, mock_session = client_and_session
        mock_session.execute = AsyncMock(side_effect=RuntimeError("PG down"))

        with (
            patch("src.main._s3") as mock_s3,
        ):
            mock_s3.upload = AsyncMock()

            resp = client.post(
                "/api/v1/knowledge/ingest",
                data=COMMON_FORM,
                files={"file": ("test.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
            )

        assert resp.status_code == 500
        assert "Database" in resp.json()["detail"]
        mock_session.rollback.assert_awaited_once()

    def test_sqs_failure_returns_500(self, client_and_session):
        client, _ = client_and_session
        with (
            patch("src.main._s3") as mock_s3,
            patch("src.main.boto3") as mock_boto3,
        ):
            mock_s3.upload = AsyncMock()
            mock_boto3.client.return_value.send_message = MagicMock(
                side_effect=RuntimeError("ElasticMQ down")
            )

            resp = client.post(
                "/api/v1/knowledge/ingest",
                data=COMMON_FORM,
                files={"file": ("test.pdf", io.BytesIO(PDF_CONTENT), "application/pdf")},
            )

        assert resp.status_code == 500
        assert "SQS" in resp.json()["detail"]


class TestHealthEndpoint:
    def test_health_returns_200(self):
        c = TestClient(app)
        resp = c.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
