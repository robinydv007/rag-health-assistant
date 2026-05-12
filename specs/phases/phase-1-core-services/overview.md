# Phase 1 — Core Services

> **Version**: 1.0
> **Status**: Planned
> **Branch**: `phase-1-core-services`
> **Follows**: Phase 0 — Bootstrap

---

## Goal

A user can ask a question and get an answer. A user can upload a document and see it enter the processing pipeline.

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM calls | Direct OpenAI/Anthropic via env vars | Circuit-breaker router is Phase 3; real streaming from day one |
| S3 local dev | MinIO in docker-compose | S3-compatible, lightweight, no AWS credentials needed locally |
| HL7/EHR parsing | Deferred to Phase 2 | Custom parser is significant scope; PDF/DOCX/TXT covers most docs |
| Query expansion | Static medical synonym dictionary | Zero latency, no API cost, sufficient for Phase 1 search quality |
| PII scrubbing | Microsoft Presidio | Runs locally, no AWS credentials, covers standard PII/PHI entities |
| Semantic search vectors | Placeholder (768-dim zeros) | Real embeddings are Phase 2; pipeline structure validated first |

---

## Scope

### In Scope

- **Chat Service**: query expansion (synonym dict) → Weaviate hybrid search → score-based rerank → direct LLM call (streaming) → SSE response → audit log write
- **Uploader Service**: multipart file upload → MinIO → PostgreSQL `documents` insert → SQS 1 publish → HTTP 202
- **Doc Processing Service**: SQS 1 consumer → Presidio PII scrub → PDF/DOCX/TXT parse → 512-token overlapping chunks → SQS 2 publish → PostgreSQL status update
- **`GET /knowledge/history`** paginated query history endpoint
- **MinIO** service added to docker-compose.yml
- **Shared clients**: S3 client wrapper, LLM client wrapper, medical synonym dictionary

### Out of Scope

- HL7/EHR parsing (Phase 2)
- Real embeddings — Chat Service uses placeholder zero-vectors; search quality is low by design (Phase 2)
- LLM Router with circuit breaker and Llama fallback (Phase 3)
- Cross-encoder or Cohere re-ranking (Phase 3 / ENH-002)
- Production AWS infrastructure
- Admin Service operations (Phase 3)
- Observability stack (Phase 4)

---

## Deliverables

| Deliverable | Verification command |
|-------------|---------------------|
| Uploader ingest endpoint | `curl -X POST .../ingest` → HTTP 202; MinIO object exists; `documents` row inserted; SQS 1 message visible |
| Doc Processing pipeline | Consume SQS 1 → PII scrubbed → chunked → SQS 2 message count increases → `documents.status = processing` |
| Chat Service ask endpoint | `curl -X POST .../ask` → SSE token stream with sources |
| Query audit log | After `/ask`, `SELECT * FROM query_history` shows new row |
| History endpoint | `GET /knowledge/history?user_id=...` → paginated results with correct schema |
| All unit + integration tests | `pytest services/ shared/ -v` exits 0 |
| Linting and type checks | `ruff check services/ shared/` and `mypy services/ shared/` exit 0 |
| CI | GitHub Actions workflow passes on clean push to `phase-1-core-services` branch |

---

## Acceptance Criteria

1. `POST /api/v1/knowledge/ingest` with a PDF → HTTP 202; file stored in MinIO; row inserted in `documents` with `status=pending`; message published to SQS 1
2. Doc Processing consumes SQS 1 message → downloads from MinIO → scrubs PII → parses → chunks → publishes to SQS 2 → updates `documents.status = processing`
3. `POST /api/v1/knowledge/ask` with a question → SSE stream of tokens; final event includes sources list
4. Every `/ask` call — including errors — writes exactly one row to `query_history`
5. `GET /api/v1/knowledge/history` returns paginated results matching the API reference schema
6. `pytest services/ shared/ -v` — all tests pass (unit + integration)
7. CI pipeline passes on a clean push to `phase-1-core-services` branch
