"""Admin Service — internal ops: re-index, alias swap, DLQ management, health check."""

import uuid

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

app = FastAPI(title="Admin Service", version="0.1.0")


class ReindexRequest(BaseModel):
    reason: str = ""


@app.get("/api/v1/health")
async def health() -> JSONResponse:
    # Phase 3: aggregate health from all services, queues, and databases
    return JSONResponse({"status": "healthy", "service": "admin-service"})


@app.post("/api/v1/admin/reindex", status_code=202)
async def reindex(request: ReindexRequest) -> JSONResponse:
    # Phase 0 stub — Phase 3: create shadow index, queue all documents
    job_id = str(uuid.uuid4())
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "shadow_index": "knowledge-v-stub",
            "docs_queued": 0,
            "status": "in_progress",
            "stub": True,
        },
    )


@app.get("/api/v1/admin/dlq")
async def dlq_status() -> JSONResponse:
    # Phase 3: inspect all DLQs via boto3
    return JSONResponse({
        "stub": True,
        "dlq_1": {"count": 0, "messages": []},
        "dlq_2": {"count": 0, "messages": []},
        "dlq_3": {"count": 0, "messages": []},
    })


@app.post("/api/v1/admin/dlq/requeue")
async def dlq_requeue(queue: str, message_ids: list[str]) -> JSONResponse:
    # Phase 3: move messages from DLQ back to main queue
    return JSONResponse({"stub": True, "requeued": 0, "failed": 0})
