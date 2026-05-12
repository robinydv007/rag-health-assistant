"""Uploader Service — accepts document uploads, writes to S3, publishes to SQS 1."""

import uuid

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from shared.models.document import DocType

app = FastAPI(title="Uploader Service", version="0.1.0")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "uploader-service"})


@app.post("/api/v1/knowledge/ingest", status_code=202)
async def ingest(
    file: UploadFile = File(...),
    title: str = Form(...),
    doc_type: DocType = Form(...),
    target_index: str = Form("live"),
) -> JSONResponse:
    # Phase 0 stub — validates input shape, returns 202 with mock IDs
    # Phase 1: upload to S3 → insert PG record → publish SQS 1
    job_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "doc_id": doc_id,
            "status": "pending",
            "status_url": f"/api/v1/knowledge/history?doc_id={doc_id}",
            "stub": True,
        },
    )
