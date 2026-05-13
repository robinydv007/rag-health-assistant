"""Embedding client with provider abstraction.

Switch between HuggingFace Serverless Inference API and any HTTP endpoint
by setting EMBEDDING_PROVIDER=hf_inference (default) | http_endpoint.
"""

from __future__ import annotations

import asyncio
import logging
import os
from abc import ABC, abstractmethod

import httpx

logger = logging.getLogger(__name__)

_HF_503_RETRY_LIMIT = 5
_HF_503_RETRY_DELAY = 20.0  # seconds; HF sends estimated_time in response


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one 768-dim vector per input text."""


class HFInferenceClient(EmbeddingClient):
    """Calls the HuggingFace Serverless Inference feature-extraction pipeline.

    Request:  POST {url}  body: {"inputs": ["text", ...]}
    Response: [[float, ...], ...]  (N vectors × 768 dims for BiomedBERT)

    Retries up to _HF_503_RETRY_LIMIT times when the model is cold-starting
    (HTTP 503 with {"estimated_time": N}).
    """

    def __init__(self, url: str, api_key: str) -> None:
        self._url = url
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not self._url:
            raise ValueError(
                "HF_INFERENCE_URL must be set when EMBEDDING_PROVIDER=hf_inference"
            )
        payload = {"inputs": texts}
        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(_HF_503_RETRY_LIMIT):
                resp = await client.post(self._url, json=payload, headers=self._headers)
                if resp.status_code == 503:
                    wait = _HF_503_RETRY_DELAY
                    try:
                        wait = float(resp.json().get("estimated_time", _HF_503_RETRY_DELAY))
                    except Exception:
                        pass
                    logger.warning(
                        "HF model loading (503) — attempt %d/%d, retrying in %.0fs",
                        attempt + 1,
                        _HF_503_RETRY_LIMIT,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
        raise RuntimeError(
            f"HF Inference API returned 503 after {_HF_503_RETRY_LIMIT} retries"
        )


class HTTPEndpointClient(EmbeddingClient):
    """Calls any HTTP model server that speaks the HF feature-extraction contract.

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


def get_embedding_client() -> EmbeddingClient:
    """Return the configured embedding client based on EMBEDDING_PROVIDER.

    URL validation is deferred to embed() time so modules can be imported and
    tested without requiring all env vars to be present at import time.
    """
    provider = os.environ.get("EMBEDDING_PROVIDER", "hf_inference")
    if provider == "hf_inference":
        url = os.environ.get("HF_INFERENCE_URL", "")
        api_key = os.environ.get("HF_API_KEY", "")
        return HFInferenceClient(url=url, api_key=api_key)
    if provider == "http_endpoint":
        url = os.environ.get("EMBEDDING_ENDPOINT_URL", "")
        api_key = os.environ.get("EMBEDDING_API_KEY")
        return HTTPEndpointClient(url=url, api_key=api_key)
    raise ValueError(
        f"Unknown EMBEDDING_PROVIDER '{provider}'. Supported: hf_inference, http_endpoint"
    )
