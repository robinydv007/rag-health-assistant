"""Uploader Service — accepts document uploads, stores in S3, publishes to SQS 1."""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import boto3
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.clients.s3_client import make_s3_client
from shared.config.settings import BaseServiceSettings
from shared.models.document import DocType
from shared.models.messages import SQS1Message

from .db import get_session

logger = logging.getLogger(__name__)

app = FastAPI(title="Uploader Service", version="0.2.0")

_settings = BaseServiceSettings()

_s3 = make_s3_client(
    bucket=_settings.s3_bucket,
    region=_settings.aws_region,
    endpoint_url=_settings.s3_endpoint_url,
    minio_user=_settings.minio_root_user if _settings.s3_endpoint_url else None,
    minio_password=_settings.minio_root_password if _settings.s3_endpoint_url else None,
)

_ALLOWED_CONTENT_TYPES = frozenset({
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
})

# Extension fallback for ZIP-based Office formats (DOCX, XLSX, PPTX share PK magic)
_ZIP_EXT_TO_CONTENT_TYPE: dict[str, str] = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _sniff_content_type(data: bytes, filename: str | None) -> str | None:
    """Detect content type from magic bytes, using filename extension as tiebreaker."""
    if data[:4] == b"%PDF":
        return "application/pdf"
    # ZIP magic covers DOCX/XLSX/PPTX — disambiguate via extension
    if data[:2] == b"PK":
        ext = Path(filename).suffix.lower() if filename else ""
        return _ZIP_EXT_TO_CONTENT_TYPE.get(ext)
    if filename and Path(filename).suffix.lower() == ".txt":
        return "text/plain"
    return None


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "uploader-service"})


@app.post("/api/v1/knowledge/ingest", status_code=202)
async def ingest(
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: DocType = Form(...),
    uploaded_by: str = Form(...),
    target_index: str = Form("live"),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()
    s3_key = f"{_settings.s3_raw_prefix}/{doc_id}/{file.filename}"
    now = datetime.now(timezone.utc)

    data = await file.read()

    # Detect real content type from magic bytes; client header is untrusted
    content_type = _sniff_content_type(data, file.filename) or file.content_type
    if content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Unsupported file type '{content_type}'. "
                "Allowed types: application/pdf, "
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document, "
                "text/plain."
            ),
        )
    if content_type != file.content_type:
        logger.warning(
            "content_type mismatch: client sent %r but detected %r for %s",
            file.content_type,
            content_type,
            file.filename,
        )

    try:
        await _s3.upload(s3_key, data, content_type)
    except Exception as exc:
        logger.error("S3 upload failed for doc_id=%s: %s", doc_id, exc)
        raise HTTPException(status_code=500, detail=f"S3 upload failed: {exc}") from exc

    try:
        await session.execute(
            text("""
                INSERT INTO documents
                    (doc_id, job_id, title, doc_type, s3_key, content_type,
                     uploaded_by, target_index, status, created_at, updated_at)
                VALUES
                    (:doc_id, :job_id, :title, :doc_type, :s3_key, :content_type,
                     :uploaded_by, :target_index, 'pending', :now, :now)
            """),
            {
                "doc_id": str(doc_id),
                "job_id": str(job_id),
                "title": title,
                "doc_type": doc_type.value,
                "s3_key": s3_key,
                "content_type": content_type,
                "uploaded_by": uploaded_by,
                "target_index": target_index,
                "now": now,
            },
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        logger.error("DB insert failed for doc_id=%s: %s", doc_id, exc)
        raise HTTPException(status_code=500, detail=f"Database insert failed: {exc}") from exc

    msg = SQS1Message(
        doc_id=str(doc_id),
        s3_key=s3_key,
        content_type=content_type,
        uploaded_by=uploaded_by,
        target_index=target_index,
        job_id=str(job_id),
        uploaded_at=now,
    )
    try:
        sqs = boto3.client(
            "sqs",
            region_name=_settings.aws_region,
            endpoint_url=_settings.aws_endpoint_url,
        )
        sqs.send_message(
            QueueUrl=_settings.sqs_queue_1_url,
            MessageBody=msg.model_dump_json(),
        )
    except Exception as exc:
        logger.error("SQS 1 publish failed for doc_id=%s: %s", doc_id, exc)
        raise HTTPException(status_code=500, detail=f"SQS publish failed: {exc}") from exc

    return JSONResponse(
        status_code=202,
        content={
            "job_id": str(job_id),
            "doc_id": str(doc_id),
            "status": "pending",
            "status_url": f"/api/v1/knowledge/history?doc_id={doc_id}",
        },
    )
