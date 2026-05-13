"""FastAPI dependency providers for the Admin Service."""

from __future__ import annotations

from collections.abc import AsyncIterator

import boto3
import httpx
import weaviate
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .settings import settings

# ── PostgreSQL ────────────────────────────────────────────────────────────────

_engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
_SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    _engine, expire_on_commit=False
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with _SessionLocal() as session:
        yield session


# ── AWS SQS ───────────────────────────────────────────────────────────────────


def get_sqs_client():
    return boto3.client(
        "sqs",
        region_name=settings.aws_region,
        endpoint_url=settings.aws_endpoint_url,
    )


# ── Weaviate ──────────────────────────────────────────────────────────────────


def get_weaviate_client() -> weaviate.Client:
    return weaviate.Client(url=settings.weaviate_url)


# ── httpx (for service health pings) ─────────────────────────────────────────


async def get_http_client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=5.0) as client:
        yield client
