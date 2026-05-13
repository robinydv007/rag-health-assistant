"""LLM caller for the Chat Service.

Wraps shared.clients.llm_client. Collects the full streamed response internally
and returns it as a single string + source citations.
"""

from __future__ import annotations

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


async def get_answer(
    question: str,
    sources: list[SearchResult],
) -> tuple[str, list[SourceCitation]]:
    """Return the full LLM answer and source citations.

    Streams tokens from the LLM internally and joins them before returning,
    so the caller receives a single complete string.
    """
    user_prompt = _build_user_prompt(question, sources)
    citations = _to_citations(sources)
    tokens: list[str] = []
    async for token in stream_completion(system_prompt=_SYSTEM_PROMPT, user_prompt=user_prompt):
        tokens.append(token)
    return "".join(tokens), citations
