"""Weaviate hybrid searcher (BM25 + BiomedBERT query embedding).

Uses weaviate-client v4 API. Phase 2: zero-vector replaced with a real
BiomedBERT embedding from the shared EmbeddingClient.
"""

from __future__ import annotations

from urllib.parse import urlparse

import weaviate
import weaviate.classes as wvc

from shared.clients.embedding_client import EmbeddingClient, get_embedding_client
from shared.config.settings import BaseServiceSettings

from .models import SearchResult  # re-exported for callers that import from here

_COLLECTION = "KnowledgeChunk"
_DEFAULT_LIMIT = 5
_ALPHA = 0.5  # 50/50 vector+BM25 now that we have real embeddings

__all__ = ["SearchResult", "hybrid_search"]

# Initialised once at module load — reused across requests
_embedding_client: EmbeddingClient = get_embedding_client()


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
    """Run a hybrid BM25 + BiomedBERT vector search against Weaviate.

    Args:
        query: Original user question.
        synonym_terms: Additional terms from query expansion.
        limit: Maximum results to return.

    Returns:
        Up to *limit* :class:`SearchResult` objects, ordered by hybrid score.
    """
    full_query = " ".join([query] + synonym_terms)
    settings = BaseServiceSettings()

    # Embed the query with BiomedBERT — same model used when indexing chunks
    vectors = await _embedding_client.embed([query])
    query_vector = vectors[0]

    with _make_client(settings) as client:
        collection = client.collections.get(_COLLECTION)
        response = collection.query.hybrid(
            query=full_query,
            vector=query_vector,
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
