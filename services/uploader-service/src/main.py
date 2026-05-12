"""Uploader Service — accepts document uploads, writes to S3, publishes to SQS 1."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(title="Uploader Service", version="0.1.0")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "uploader-service"})


# TODO Phase 1: POST /api/v1/knowledge/ingest — multipart upload → S3 → PG → SQS 1 → 202
