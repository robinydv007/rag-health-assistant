"""Admin Service — aggregate health check across all services, Postgres, Weaviate, SQS."""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .settings import settings

logger = logging.getLogger(__name__)


async def check_service(client: httpx.AsyncClient, url: str) -> str:
    try:
        resp = await client.get(f"{url}/health")
        return "healthy" if resp.status_code == 200 else "unhealthy"
    except Exception:
        return "unhealthy"


async def check_postgres(session: AsyncSession) -> str:
    try:
        await session.execute(text("SELECT 1"))
        return "healthy"
    except Exception:
        return "unhealthy"


async def check_weaviate(weaviate_url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{weaviate_url}/v1/.well-known/ready")
            return "healthy" if resp.status_code == 200 else "unhealthy"
    except Exception:
        return "unhealthy"


async def get_sqs_depth(sqs_client, queue_url: str) -> int:
    try:
        resp = await _sqs_get_attributes(sqs_client, queue_url)
        return int(resp["Attributes"]["ApproximateNumberOfMessages"])
    except Exception:
        return -1


async def _sqs_get_attributes(sqs_client, queue_url: str) -> dict:
    import asyncio
    return await asyncio.to_thread(
        sqs_client.get_queue_attributes,
        QueueUrl=queue_url,
        AttributeNames=["ApproximateNumberOfMessages"],
    )


async def aggregate_health(
    session: AsyncSession,
    sqs_client,
    http_client: httpx.AsyncClient,
) -> dict:
    services = {
        "chat-service":          await check_service(http_client, settings.chat_service_url),
        "uploader-service":      await check_service(http_client, settings.uploader_service_url),
        "doc-processing-service": await check_service(
            http_client, settings.doc_processing_service_url
        ),
        "embedding-service":     await check_service(http_client, settings.embedding_service_url),
        "indexing-service":      await check_service(http_client, settings.indexing_service_url),
    }

    postgres_status = await check_postgres(session)
    weaviate_status = await check_weaviate(settings.weaviate_url)

    queues = {
        "queue_1": await get_sqs_depth(sqs_client, settings.sqs_queue_1_url),
        "queue_2": await get_sqs_depth(sqs_client, settings.sqs_queue_2_url),
        "queue_3": await get_sqs_depth(sqs_client, settings.sqs_queue_3_url),
        "dlq_1":   await get_sqs_depth(sqs_client, settings.sqs_dlq_1_url),
        "dlq_2":   await get_sqs_depth(sqs_client, settings.sqs_dlq_2_url),
        "dlq_3":   await get_sqs_depth(sqs_client, settings.sqs_dlq_3_url),
    }

    all_healthy = (
        all(v == "healthy" for v in services.values())
        and postgres_status == "healthy"
        and weaviate_status == "healthy"
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": services,
        "postgres": postgres_status,
        "weaviate": weaviate_status,
        "queues": queues,
    }
