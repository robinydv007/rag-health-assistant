"""Embedding client with provider abstraction.

Switch between OpenAI, any HTTP endpoint, or the local-dev mock by setting
EMBEDDING_PROVIDER=openai (default) | http_endpoint | mock.
"""

from __future__ import annotations

import hashlib
import logging
import math
import os
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)

_OPENAI_EMBED_URL = "https://api.openai.com/v1/embeddings"


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""


class OpenAIEmbeddingClient(EmbeddingClient):
    """Calls the OpenAI Embeddings API.

    Model: text-embedding-3-large (3072 dims) by default.
    Set EMBEDDING_PROVIDER=openai, OPENAI_API_KEY, and optionally
    OPENAI_EMBEDDING_MODEL to use.

    Request:  POST https://api.openai.com/v1/embeddings
              body: {"model": "...", "input": ["text", ...]}
    Response: {"data": [{"index": 0, "embedding": [...]}, ...]}
    """

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not self._api_key:
            raise ValueError("OPENAI_API_KEY must be set when EMBEDDING_PROVIDER=openai")
        payload = {"model": self._model, "input": texts}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(_OPENAI_EMBED_URL, json=payload, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()["data"]
            # Sort by index to guarantee order matches input
            data.sort(key=lambda d: d["index"])
            return [d["embedding"] for d in data]


class HTTPEndpointClient(EmbeddingClient):
    """Calls any HTTP model server that accepts a JSON embedding request.

    Compatible with: Triton, vLLM, or a custom FastAPI wrapper around transformers.
    Set EMBEDDING_PROVIDER=http_endpoint and EMBEDDING_ENDPOINT_URL to use.
    EMBEDDING_API_KEY is optional — omit if the endpoint has no auth.

    Request:  POST {url}  body: {"inputs": ["text", ...]}
    Response: [[float, ...], ...]
    """

    def __init__(self, url: str, api_key: str | None = None) -> None:
        self._url = url
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        payload = {"inputs": texts}
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(self._url, json=payload, headers=self._headers)
            resp.raise_for_status()
            return resp.json()


class MockEmbeddingClient(EmbeddingClient):
    """Deterministic 3072-dim unit-norm vectors derived from text hash.

    No network calls, no API key required. Designed for local development
    and CI environments without an OpenAI key. Set EMBEDDING_PROVIDER=mock
    to use.

    Same text always produces the same vector (reproducible), so local
    Weaviate search via BM25 (keyword) works correctly end-to-end even
    though the vectors are not semantically meaningful.
    """

    _DIMS = 3072

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._hash_to_unit_vector(t) for t in texts]

    @classmethod
    def _hash_to_unit_vector(cls, text: str) -> list[float]:
        # 96 SHA-256 rounds × 32 bytes = 3072 raw bytes mapped to [-1, 1]
        raw: list[float] = []
        for i in range(96):
            digest = hashlib.sha256(f"{text}:{i}".encode()).digest()
            raw.extend((b - 127.5) / 127.5 for b in digest)
        magnitude = math.sqrt(sum(v * v for v in raw)) or 1.0
        return [v / magnitude for v in raw]


def get_embedding_client() -> EmbeddingClient:
    """Return the configured embedding client based on EMBEDDING_PROVIDER.

    Key validation is deferred to embed() time so modules can be imported
    and tested without requiring all env vars to be present at import time.
    """
    provider = os.environ.get("EMBEDDING_PROVIDER", "openai")
    if provider == "openai":
        return OpenAIEmbeddingClient(
            api_key=os.environ.get("OPENAI_API_KEY", ""),
            model=os.environ.get("OPENAI_EMBEDDING_MODEL", "text-embedding-3-large"),
        )
    if provider == "http_endpoint":
        return HTTPEndpointClient(
            url=os.environ.get("EMBEDDING_ENDPOINT_URL", ""),
            api_key=os.environ.get("EMBEDDING_API_KEY"),
        )
    if provider == "mock":
        return MockEmbeddingClient()
    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER '{provider}'. Supported: openai, http_endpoint, mock"
    )
