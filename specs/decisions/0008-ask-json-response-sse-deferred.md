# ADR 0008 — /ask Returns JSON in Phase 1–2; SSE Deferred to ENH-006

> **Status**: accepted
> **Date**: 2026-05-13
> **Supersedes**: N/A
> **Amends**: [ADR 0007](0007-fastapi-backend-framework.md) — removes SSE from Phase 1–2 scope; SSE remains the long-term target

## Context

ADR 0007 identified SSE streaming as requirement #1 for the FastAPI choice: the Chat Service must stream LLM tokens to the client as they arrive. When Phase 1 was implemented, the `/ask` endpoint was initially built with `StreamingResponse` and `text/event-stream`.

During Phase 1 integration we evaluated the client-side impact:

- SSE requires the caller to implement an event-stream reader, handle reconnection, and parse `data:` lines — non-trivial in every client environment (browser `EventSource`, curl, Python `httpx`, REST test tools)
- Phase 1 and Phase 2 have no production client yet; the only consumers are integration tests and manual `curl` calls
- The internal LLM call is already async — tokens are streamed from the provider to the service; collecting them into a single string adds at most ~200–500 ms of additional latency for typical queries, which is acceptable for Phase 1–2
- A plain JSON response (`{"answer": str, "sources": [...]}`) is usable by every HTTP client without any special handling

The decision to ship SSE adds client complexity for no concrete Phase 1–2 benefit. The complexity cost is front-loaded; the streaming benefit is only realized when a real client (web app, mobile app) is built in Phase 3+.

## Decision

`POST /api/v1/knowledge/ask` returns a **single synchronous JSON response** in Phase 1 and Phase 2:

```json
{
  "answer": "<full answer text>",
  "sources": [
    {"doc_id": "...", "title": "...", "page": 3}
  ]
}
```

The LLM is still called with streaming internally — tokens are collected with `async for` and joined before responding. This preserves compatibility with provider streaming APIs and keeps `llm_caller.py` easy to convert back to true streaming.

SSE streaming is tracked as **ENH-006 (P3)** in the backlog and will be re-evaluated when a real browser/mobile client is introduced (target: Phase 3 or later).

ADR 0007's FastAPI choice remains fully valid — all other justifications (async concurrency, Pydantic validation, OpenAPI generation, ML ecosystem compatibility) are unaffected by this deferral.

## Consequences

### Positive
- Zero client-side streaming complexity in Phase 1–2
- Integration tests use standard `httpx.post()` — no SSE reader logic
- `curl` smoke tests work without `--no-buffer` or event-stream parsing
- Easy to roll forward: `get_answer()` in `llm_caller.py` already collects from an async generator; converting to yield-based streaming requires only the FastAPI endpoint wrapper

### Negative
- Time-to-first-token latency is worse for end users — they see nothing until the full answer is ready
- The declared API contract (SSE) diverges from the implementation until ENH-006 ships; all callers must be informed when SSE is re-introduced

### Risks
- If a Phase 2 demo requires visible streaming, ENH-006 must be fast-tracked — mitigated by the clean internal architecture (the LLM call already streams; only the HTTP layer changes)

## Alternatives Considered

| Option | Why Rejected |
|--------|-------------|
| **Ship SSE as designed** | Adds event-stream reader logic to every test and smoke-test; zero benefit until a real browser client exists |
| **Optional `?stream=true` query param** | Adds branching complexity for one call path; deferred; can be added with ENH-006 |
| **WebSocket** | More complex than SSE; appropriate only if bidirectional real-time messaging is needed (it is not) |
