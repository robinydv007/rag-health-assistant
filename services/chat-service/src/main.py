"""Chat Service — query expand → hybrid search → rerank → LLM call + audit log."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.query import AskRequest

from .db import get_session
from .expander import expand_query
from .llm_caller import get_answer
from .reranker import rerank
from .searcher import SearchResult, hybrid_search

logger = logging.getLogger(__name__)

app = FastAPI(title="Chat Service", version="0.2.0")


@app.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "healthy", "service": "chat-service"})


@app.post("/api/v1/knowledge/ask")
async def ask(
    request: AskRequest,
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Return a complete LLM answer to *request.question*.

    Every call — including errors — writes one row to query_history (HC-2).
    """
    start_ms = int(time.time() * 1000)
    top_sources: list[SearchResult] = []
    answer = ""
    citations = []

    try:
        question, synonyms = expand_query(request.question)
        raw_results = await hybrid_search(question, synonyms)
        top_sources = rerank(raw_results)
        answer, citations = await get_answer(question, top_sources)
    except Exception as exc:
        logger.error("Error in /ask for user=%s: %s", request.user_id, exc, exc_info=True)
        answer = f"Error: {exc}"
    finally:
        await _write_audit_log(session, request, top_sources, answer, start_ms)

    return JSONResponse({
        "answer": answer,
        "sources": [c.model_dump() for c in citations],
    })


async def _write_audit_log(
    session: AsyncSession,
    request: AskRequest,
    sources: list[SearchResult],
    response_text: str,
    start_ms: int,
) -> None:
    """Write one row to query_history — always called, even on error (HC-2)."""
    latency_ms = int(time.time() * 1000) - start_ms
    sources_json = json.dumps([
        {"doc_id": s.doc_id, "title": s.title, "page": s.page_num}
        for s in sources
    ])
    try:
        await session.execute(
            text("""
                INSERT INTO query_history
                    (query_id, user_id, session_id, question, response, sources,
                     model_used, latency_ms, index_queried, created_at)
                VALUES
                    (:query_id, :user_id, :session_id, :question, :response,
                     CAST(:sources AS jsonb), :model_used, :latency_ms, 'live', :now)
            """),
            {
                "query_id": str(uuid.uuid4()),
                "user_id": request.user_id,
                "session_id": request.session_id,
                "question": request.question,
                "response": response_text or "",
                "sources": sources_json,
                "model_used": "mock" if not sources else "hybrid-search",
                "latency_ms": latency_ms,
                "now": datetime.now(timezone.utc),
            },
        )
        await session.commit()
    except Exception as exc:
        logger.error("CRITICAL: audit log write failed for user=%s: %s", request.user_id, exc)


@app.get("/api/v1/knowledge/history")
async def history(
    user_id: str = Query(...),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    """Return paginated query history for *user_id*."""
    result = await session.execute(
        text("""
            SELECT query_id, user_id, session_id, question, response, sources,
                   model_used, latency_ms, index_queried, pii_detected, created_at
            FROM query_history
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"user_id": user_id, "limit": limit, "offset": offset},
    )
    rows = result.mappings().all()

    count_result = await session.execute(
        text("SELECT COUNT(*) FROM query_history WHERE user_id = :user_id"),
        {"user_id": user_id},
    )
    total = count_result.scalar() or 0

    queries = [
        {
            "query_id": str(row["query_id"]),
            "user_id": row["user_id"],
            "session_id": row["session_id"],
            "question": row["question"],
            "response": row["response"],
            "sources": row["sources"],
            "model_used": row["model_used"],
            "latency_ms": row["latency_ms"],
            "index_queried": row["index_queried"],
            "pii_detected": row["pii_detected"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        }
        for row in rows
    ]

    return JSONResponse({"queries": queries, "total": total, "limit": limit, "offset": offset})
