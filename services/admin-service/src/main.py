"""Admin Service — internal ops: re-index, alias swap, DLQ management, health check."""

from __future__ import annotations

import logging

import httpx
from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from .deps import get_db, get_http_client, get_sqs_client, get_weaviate_client
from .dlq import inspect_dlq, requeue_messages
from .health import aggregate_health
from .reindex import swap_index, trigger_reindex
from .settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="Admin Service", version="0.3.0")


class ReindexRequest(BaseModel):
    reason: str = ""


class RequeueRequest(BaseModel):
    queue: str
    message_ids: list[str]


@app.get("/api/v1/health")
async def health(
    session: AsyncSession = Depends(get_db),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> JSONResponse:
    sqs_client = get_sqs_client()
    result = await aggregate_health(session, sqs_client, http_client)
    status_code = 200 if result["status"] == "healthy" else 207
    return JSONResponse(result, status_code=status_code)


@app.post("/api/v1/admin/reindex", status_code=202)
async def reindex(
    request: ReindexRequest,
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    sqs_client = get_sqs_client()
    weaviate_client = get_weaviate_client()
    result = await trigger_reindex(
        reason=request.reason,
        session=session,
        sqs_client=sqs_client,
        weaviate_client=weaviate_client,
    )
    return JSONResponse(result, status_code=202)


@app.post("/api/v1/admin/swap-index")
async def swap(
    session: AsyncSession = Depends(get_db),
) -> JSONResponse:
    weaviate_client = get_weaviate_client()
    result = await swap_index(session=session, weaviate_client=weaviate_client)
    return JSONResponse(result)


@app.get("/api/v1/admin/dlq")
async def dlq_status() -> JSONResponse:
    sqs_client = get_sqs_client()
    dlq_1 = await inspect_dlq(sqs_client, settings.sqs_dlq_1_url)
    dlq_2 = await inspect_dlq(sqs_client, settings.sqs_dlq_2_url)
    dlq_3 = await inspect_dlq(sqs_client, settings.sqs_dlq_3_url)
    return JSONResponse({"dlq_1": dlq_1, "dlq_2": dlq_2, "dlq_3": dlq_3})


@app.post("/api/v1/admin/dlq/requeue")
async def dlq_requeue(request: RequeueRequest) -> JSONResponse:
    sqs_client = get_sqs_client()
    queue_map = {
        "queue_1": settings.sqs_queue_1_url,
        "queue_2": settings.sqs_queue_2_url,
        "queue_3": settings.sqs_queue_3_url,
    }
    dlq_map = {
        "queue_1": settings.sqs_dlq_1_url,
        "queue_2": settings.sqs_dlq_2_url,
        "queue_3": settings.sqs_dlq_3_url,
    }
    main_queue_url = queue_map.get(request.queue)
    dlq_url = dlq_map.get(request.queue)
    if not main_queue_url or not dlq_url:
        return JSONResponse(
            {"error": f"Unknown queue '{request.queue}'. Use queue_1, queue_2, or queue_3."},
            status_code=400,
        )
    result = await requeue_messages(sqs_client, dlq_url, main_queue_url, request.message_ids)
    return JSONResponse(result)
