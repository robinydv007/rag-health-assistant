"""Weaviate writer — upserts KnowledgeChunk objects with pre-computed vectors."""

from __future__ import annotations

import logging
import uuid as _uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import weaviate

from shared.models.messages import SQS3Message

logger = logging.getLogger(__name__)

_COLLECTION = "KnowledgeChunk"
EMBEDDED_MODEL = "text-embedding-3-large"


def _make_client(weaviate_url: str) -> weaviate.WeaviateClient:
    parsed = urlparse(weaviate_url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 8080
    return weaviate.connect_to_custom(
        http_host=host,
        http_port=port,
        http_secure=False,
        grpc_host=host,
        grpc_port=50051,
        grpc_secure=False,
        auth_credentials=None,
    )


def _chunk_uuid(chunk_id: str) -> str:
    """Deterministic UUID v5 from chunk_id — enables idempotent retries."""
    return str(_uuid.uuid5(_uuid.NAMESPACE_DNS, chunk_id))


class WeaviateWriter:
    def __init__(self, weaviate_url: str) -> None:
        self._url = weaviate_url

    def upsert(self, msg: SQS3Message, title: str = "") -> None:
        """Upsert one KnowledgeChunk — idempotent via deterministic UUID."""
        props = {
            "docId": msg.doc_id,
            "chunkId": msg.chunk_id,
            "chunkIdx": msg.metadata.chunk_idx,
            "text": msg.text,
            "docType": msg.metadata.doc_type.value,
            "title": title,
            "pageNum": msg.metadata.page_num,
            "version": msg.metadata.version,
            "embeddedModel": EMBEDDED_MODEL,
            "indexedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        chunk_uuid = _chunk_uuid(msg.chunk_id)

        with _make_client(self._url) as client:
            collection = client.collections.get(_COLLECTION)
            try:
                collection.data.insert(
                    properties=props,
                    vector=msg.embedding,
                    uuid=chunk_uuid,
                )
            except Exception as e:
                if "already exists" in str(e).lower() or "422" in str(e):
                    collection.data.replace(
                        uuid=chunk_uuid,
                        properties=props,
                        vector=msg.embedding,
                    )
                else:
                    raise

        logger.debug("Upserted KnowledgeChunk chunk_id=%s", msg.chunk_id)
