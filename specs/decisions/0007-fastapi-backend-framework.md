# ADR 0007 — FastAPI as the Backend Framework

> **Status**: accepted
> **Date**: 2026-05-12
> **Supersedes**: N/A

## Context

All six services in this system are Python applications. The framework choice applies primarily to the three HTTP-facing services: **Chat Service**, **Uploader Service**, and **Admin Service**. The three pipeline services (Doc Processing, Embedding, Indexing) are SQS consumers and do not expose HTTP, but they share the same codebase conventions.

Key requirements that drive the framework choice:

1. **SSE streaming** — the Chat Service must stream LLM tokens to the client as they arrive. This requires true async HTTP support at the framework level; a synchronous framework would block the worker thread for the entire LLM call duration.
2. **ML/Python ecosystem** — the services call BioGPT, SciBERT, LangChain, and the OpenAI/Anthropic SDKs. These are Python-native; the framework must not fight the ecosystem.
3. **High concurrency at low cost** — 500+ concurrent users; we scale horizontally on ECS Fargate. Per-task memory is billed, so a lightweight async framework is preferable to thread-per-request models.
4. **OpenAPI auto-generation** — the spec (ADR context: `specs/architecture/openapi.yaml`) is maintained by hand, but runtime validation against the schema is a bonus. FastAPI generates and serves `/docs` automatically, useful for internal tooling.
5. **Development speed** — small team; Pydantic-based request/response models reduce boilerplate and catch schema errors at the boundary.

## Decision

Use **FastAPI** (with Uvicorn/Gunicorn) for all HTTP-facing services.

- Uvicorn as the ASGI server; Gunicorn as the process manager in production (multi-worker)
- Pydantic v2 models for request/response validation
- `StreamingResponse` with `text/event-stream` media type for the Chat Service SSE endpoint
- LangChain's async callback handlers (`AsyncIteratorCallbackHandler`) feed directly into the SSE stream

## Consequences

### Positive
- Native async (`async def`) throughout — one thread handles many concurrent SSE streams without blocking
- Pydantic models give automatic request validation and clear schema documentation with zero extra code
- `/docs` (Swagger UI) and `/redoc` served automatically — useful for internal consumers and QA
- First-class support for `StreamingResponse` and `BackgroundTasks` — both needed by Chat and Uploader
- LangChain, Weaviate client, and all ML SDKs have async APIs that pair naturally with FastAPI's event loop
- Strong typing makes refactoring safe; mypy and Pyright work well with Pydantic models

### Negative
- Uvicorn's single-event-loop model means CPU-bound work (PII scanning in Doc Processing) must be offloaded to `asyncio.run_in_executor` or run in a separate process pool — a non-obvious pattern for developers new to async Python
- FastAPI's dependency injection system has a learning curve; misused, it introduces hidden coupling
- Auto-generated OpenAPI schema from FastAPI will diverge from our hand-maintained `openapi.yaml` if not kept in sync — treat the hand-maintained file as the source of truth

### Risks
- If a service needs to do sustained heavy CPU work synchronously (unlikely given the pipeline is async), FastAPI's async model will require process-based parallelism. Mitigation: pipeline services are SQS consumers, not HTTP servers, so this risk is contained to the HTTP-facing trio.

## Alternatives Considered

| Option | Why Rejected |
|--------|-------------|
| **Flask** | Synchronous by default. SSE streaming requires Werkzeug's `Response(stream_with_context)` which ties up a worker thread per stream. Scaling 500 concurrent SSE streams would require 500 threads — impractical. Async Flask exists but is not idiomatic; FastAPI is purpose-built for this. |
| **Django REST Framework** | ORM-centric and significantly heavier. Django's ORM adds little value (we use SQLAlchemy/asyncpg directly for audit writes). DRF's synchronous request handling has the same SSE problem as Flask. Boot time and memory footprint are higher. |
| **Starlette (direct)** | FastAPI is built on Starlette and adds Pydantic validation, dependency injection, and OpenAPI generation on top. Using Starlette directly would mean re-implementing those layers. No reason to go lower unless we hit a specific FastAPI limitation. |
| **Express (Node.js)** | The entire ML stack (BioGPT, SciBERT, LangChain, OpenAI SDK) is Python. Running Node services that shell out to Python scripts, or splitting the codebase across two runtimes, adds operational complexity with no benefit. |
| **Litestar** | Modern, performant, opinionated — comparable to FastAPI. Smaller ecosystem and fewer LangChain/Weaviate integration examples. FastAPI's larger community is an advantage when debugging ML-adjacent async issues. |
