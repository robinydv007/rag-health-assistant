"""LLM streaming caller for the Chat Service.

Wraps shared.clients.llm_client and yields JSON-encoded SSE data lines
suitable for FastAPI's StreamingResponse.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from shared.clients.llm_client import stream_completion
from shared.models.query import SourceCitation

from .searcher import SearchResult

_SYSTEM_PROMPT = (
    "You are a clinical knowledge assistant for healthcare staff. "
    "Answer questions ONLY using the provided source excerpts. "
    "If the sources do not contain enough information, say so explicitly. "
    "Always cite the source document title and page number for each claim. "
    "Never include patient-identifiable information in your response."
)


def _build_user_prompt(question: str, sources: list[SearchResult]) -> str:
    source_text = "\n\n".join(
        f"[Source {i+1}] {s.title} (page {s.page_num}):\n{s.text}"
        for i, s in enumerate(sources)
    )
    return f"Sources:\n{source_text}\n\nQuestion: {question}"


def _to_citations(sources: list[SearchResult]) -> list[SourceCitation]:
    return [
        SourceCitation(
            doc_id=s.doc_id,
            title=s.title,
            page=s.page_num,
            chunk=s.text[:200] if s.text else None,
        )
        for s in sources
    ]


async def stream_answer(
    question: str,
    sources: list[SearchResult],
) -> AsyncIterator[str]:
    """Yield SSE-formatted data strings for the /ask endpoint.

    Each yield is a complete ``data: {...}\\n\\n`` line. The final event
    includes ``done=true`` and the source citations list.

    Args:
        question: The user's question.
        sources: Top-ranked search results to pass as context.

    Yields:
        SSE data lines as strings.
    """
    user_prompt = _build_user_prompt(question, sources)
    citations = _to_citations(sources)

    async for token in stream_completion(system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt):
        payload = json.dumps({"token": token, "done": False})
        yield f"data: {payload}\n\n"

    final = json.dumps({
        "token": "",
        "done": True,
        "sources": [c.model_dump() for c in citations],
    })
    yield f"data: {final}\n\n"
