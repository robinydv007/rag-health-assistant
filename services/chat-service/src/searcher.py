"""Weaviate hybrid searcher (BM25 + placeholder zero-vector).

Uses weaviate-client v4 API. In Phase 1 the nearVector component uses a
768-dim zero-vector; real embeddings arrive in Phase 2. BM25 keyword search
drives result quality in this phase.
"""

from __future__ import annotations

from urllib.parse import urlparse

import weaviate
import weaviate.classes as wvc

from shared.config.settings import BaseServiceSettings

from .models import SearchResult  # re-exported for callers that import from here

_COLLECTION = "KnowledgeChunk"
_VECTOR_DIM = 768
_ZERO_VECTOR = [0.0] * _VECTOR_DIM
_DEFAULT_LIMIT = 5
_ALPHA = 0.4  # 40% vector, 60% BM25 (zero-vectors make vector side ~noise)

__all__ = ["SearchResult", "hybrid_search"]


def _make_client(settings: BaseServiceSettings) -> weaviate.WeaviateClient:
    parsed = urlparse(settings.weaviate_url)
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


async def hybrid_search(
    query: str,
    synonym_terms: list[str],
    limit: int = _DEFAULT_LIMIT,
) -> list[SearchResult]:
    """Run a hybrid BM25 + vector search against Weaviate.

    The query string is augmented with synonym terms by joining them with
    spaces so Weaviate BM25 can score against the expanded vocabulary.

    Args:
        query: Original user question.
        synonym_terms: Additional terms from query expansion.
        limit: Maximum results to return.

    Returns:
        Up to *limit* :class:`SearchResult` objects, ordered by hybrid score.
    """
    full_query = " ".join([query] + synonym_terms)
    settings = BaseServiceSettings()

    with _make_client(settings) as client:
        collection = client.collections.get(_COLLECTION)
        response = collection.query.hybrid(
            query=full_query,
            vector=_ZERO_VECTOR,
            alpha=_ALPHA,
            limit=limit,
            return_metadata=wvc.query.MetadataQuery(score=True),
        )

    results = []
    for obj in response.objects:
        props = obj.properties
        score = obj.metadata.score if obj.metadata else 0.0
        results.append(
            SearchResult(
                doc_id=str(props.get("docId", "")),
                chunk_id=str(props.get("chunkId", "")),
                text=str(props.get("text", "")),
                title=str(props.get("title", "")),
                page_num=int(props.get("pageNum", 0)),
                score=float(score or 0.0),
            )
        )
    return results
