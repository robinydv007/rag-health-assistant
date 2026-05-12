# Phase 1 — Implementation Plan

```
Sequential:  Group 0 → (Groups 1 + 2 + 3 in parallel) → Group 4 → Group 5
```

---

## Group 0 — Infrastructure & Shared Prerequisites

**Sequential.** Blocks all other groups.
**Dependencies**: Phase 0 docker-compose.yml complete
**Commit**: `feat(infra): add MinIO, shared clients, synonym dict, Phase 1 deps`

### Tasks

1. Add MinIO service to `docker-compose.yml` (image: `minio/minio`, port 9000/9001, bucket auto-created via `mc mb`)
2. Create `shared/clients/s3_client.py` — async boto3 S3 wrapper; endpoint URL from `S3_ENDPOINT_URL` env var (empty = real AWS, set = MinIO/localstack)
3. Create `shared/clients/llm_client.py` — async OpenAI/Anthropic streaming client; provider via `LLM_PROVIDER` env var (`openai` | `anthropic`); mock mode via `LLM_MOCK=true` returns fixture tokens
4. Create `shared/data/medical_synonyms.yaml` — 100–200 entries covering common medical abbreviations and synonyms (MI/myocardial infarction, HTN/hypertension, DM/diabetes mellitus, etc.)
5. Create `shared/utils/query_expander.py` — loads synonym dict, returns original query + matched synonym terms as expanded list
6. Add Phase 1 Python deps to each service `requirements.txt` that needs them: `presidio-analyzer`, `presidio-anonymizer`, `pdfplumber`, `python-docx`, `openai`, `anthropic`, `tiktoken`, `weaviate-client`
7. Update `.env.example` with new vars: `S3_ENDPOINT_URL`, `S3_BUCKET_NAME`, `LLM_PROVIDER`, `LLM_MOCK`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`

---

## Group 1 — Uploader Service

**Parallel with Groups 2 and 3.**
**Dependencies**: Group 0 complete (S3 client, updated compose)
**Commit**: `feat(uploader): implement ingest endpoint`

### Tasks

1. Implement `POST /api/v1/knowledge/ingest` multipart handler (`services/uploader-service/src/main.py`):
   - Validate file type — accept PDF, DOCX, TXT only; return HTTP 422 for all others
   - Generate `doc_id` (UUID4) and `job_id` (UUID4)
   - Upload file to MinIO/S3 at key `raw-docs/{doc_id}/{original_filename}` via shared S3 client
   - Insert row into `documents` table via SQLAlchemy (async): `status=pending`, all fields populated
   - Publish SQS 1 message matching `DocProcessingJob` schema from `shared/models/messages.py`
   - Return HTTP 202 `{ job_id, doc_id, status: "pending", status_url }`
2. Add async SQLAlchemy session factory (`services/uploader-service/src/db.py`) — connection string from settings
3. Unit tests (`services/uploader-service/tests/test_ingest.py`):
   - Valid PDF upload → HTTP 202 + correct response shape
   - Invalid file type → HTTP 422
   - S3 upload failure → HTTP 500 with error detail
   - PostgreSQL insert failure → HTTP 500
4. Integration test (`services/uploader-service/tests/test_ingest_integration.py`): real MinIO + real PostgreSQL, verify MinIO object exists, PG row inserted, SQS 1 message count increases

---

## Group 2 — Doc Processing Service

**Parallel with Groups 1 and 3.**
**Dependencies**: Group 0 complete
**Commit**: `feat(doc-processing): implement SQS consumer, PII scrub, parse, chunk`

### Tasks

1. Implement SQS 1 consumer loop (`services/doc-processing/src/main.py`):
   - Long-poll SQS 1 (`WaitTimeSeconds=20`, `MaxNumberOfMessages=1`)
   - Download file from MinIO/S3 via shared S3 client
   - Dispatch to parser by `content_type` field from SQS message
   - On success: delete SQS message, publish SQS 2, update PG status
   - On failure: log error, do NOT delete message — let visibility timeout expire → DLQ after 3 retries
2. Implement Presidio PII scrubber (`services/doc-processing/src/scrubber.py`):
   - `AnalyzerEngine` + `AnonymizerEngine`
   - Entities: `PERSON`, `DATE_TIME`, `US_SSN`, `US_ITIN`, `PHONE_NUMBER`, `EMAIL_ADDRESS`, `LOCATION`, `MEDICAL_LICENSE`, `NPI`
   - Replacement pattern: `[REDACTED-{entity_type}]`
3. Implement parsers (`services/doc-processing/src/parsers/`):
   - `pdf_parser.py` — pdfplumber; extract text page-by-page; return `List[Tuple[str, int]]` (text, page_num)
   - `docx_parser.py` — python-docx; extract paragraphs; page_num set to 0 (no page concept)
   - `txt_parser.py` — read UTF-8 with latin-1 fallback; single page
4. Implement chunker (`services/doc-processing/src/chunker.py`):
   - tiktoken `cl100k_base` tokenizer
   - 512-token max chunks, 50-token overlap between consecutive chunks
   - Returns `List[ChunkMetadata]` with `chunk_idx`, `page_num`, `token_count`, `text`
5. Publish chunk batch to SQS 2 matching `ChunkEmbeddingJob` schema; update `documents.status = processing`; set `documents.chunks_total = len(chunks)`
6. Unit tests (`services/doc-processing/tests/`):
   - `test_scrubber.py` — verify each entity type is redacted
   - `test_pdf_parser.py` — parse fixture PDF, assert text extracted and page_num set
   - `test_docx_parser.py` — parse fixture DOCX
   - `test_txt_parser.py` — parse UTF-8 and latin-1 fixture files
   - `test_chunker.py` — verify chunk token counts ≤512, overlap ≥50 tokens between adjacent chunks
7. Integration test: place a `DocProcessingJob` message on SQS 1 → assert SQS 2 messages appear (≥1 chunk) + `documents.status = processing` + chunk text contains no raw PII

---

## Group 3 — Chat Service

**Parallel with Groups 1 and 2.**
**Dependencies**: Group 0 complete
**Commit**: `feat(chat): implement ask endpoint, SSE stream, audit log, history`

### Tasks

1. Implement query expander (`services/chat-service/src/expander.py`):
   - Load `shared/data/medical_synonyms.yaml` at startup
   - For each token in query, check for matches; return original query string + list of synonym terms
2. Implement Weaviate hybrid searcher (`services/chat-service/src/searcher.py`):
   - BM25 keyword search on `text` property using Weaviate `bm25` operator
   - `nearVector` search using 768-dim zero-vector as placeholder
   - Fuse scores: `combined = 0.6 * bm25_score + 0.4 * vector_score`
   - Return top-5 results as `List[Source]`
3. Implement score-based reranker (`services/chat-service/src/reranker.py`):
   - Sort sources by `combined_score` descending
   - Return top-3
4. Implement LLM caller with SSE streaming (`services/chat-service/src/llm_caller.py`):
   - System prompt: healthcare knowledge assistant, answer only from provided sources, always cite source and page
   - User prompt: question + formatted top-3 chunks
   - Yield `{"token": str, "done": false}` events as tokens stream
   - Final event: `{"token": "", "done": true, "sources": [...]}`
5. Implement `POST /api/v1/knowledge/ask` endpoint (`services/chat-service/src/main.py`):
   - Expand query → search → rerank → stream LLM
   - Collect full response text during stream
   - After stream completes (or on error), write row to `query_history`
   - Return `StreamingResponse` with `media_type="text/event-stream"`
6. Implement `GET /api/v1/knowledge/history` endpoint:
   - Query `query_history` by `user_id`, ordered by `created_at DESC`
   - Paginated via `limit` (default 20, max 100) and `offset`
   - Return `{ queries: [...], total: N }`
7. Unit tests (`services/chat-service/tests/`):
   - `test_expander.py` — verify synonym matches and no-match passthrough
   - `test_searcher.py` — mock Weaviate client, verify BM25 + vector query structure
   - `test_reranker.py` — verify top-3 selection by score
   - `test_llm_caller.py` — mock LLM client, verify SSE event format
   - `test_audit_log.py` — verify `query_history` row written on success and on error
8. Integration test: seed Weaviate with 3 fixture chunks (zero-vector embeddings); call `/ask`; assert SSE stream completes with `done=true`; assert `query_history` row written

---

## Group 4 — Wiring & Integration

**Sequential.** Runs after Groups 1, 2, and 3 are complete.
**Dependencies**: All three service implementations done
**Commit**: `test(integration): Phase 1 end-to-end upload and ask flow`

### Tasks

1. Verify `docker-compose up --build` starts all services healthy, including MinIO
2. End-to-end upload test:
   - POST PDF to Uploader Service
   - Assert MinIO contains the object at `raw-docs/{doc_id}/`
   - Assert `documents` row in PostgreSQL with `status=pending`
   - Assert SQS 1 message count = 1
3. End-to-end doc processing test:
   - Trigger SQS 1 consumer on test message (or allow it to poll)
   - Assert SQS 2 message count ≥1
   - Assert `documents.status = processing` in PostgreSQL
   - Assert chunk text in SQS 2 message does not contain raw PII test strings
4. End-to-end ask test:
   - Seed Weaviate with 3 fixture chunks
   - POST question to Chat Service `/ask`
   - Assert SSE stream completes with final `done=true` event
   - Assert `query_history` table has a new row for the query
5. Smoke test all 6 `/health` endpoints return HTTP 200

---

## Group 5 — Verification

**Sequential.** Runs after Group 4.
**Dependencies**: All integration tests passing
**Commit**: `chore: Phase 1 verification — all tests pass`

### Tasks

1. Run full test suite: `pytest services/ shared/ -v --tb=short` → exit 0
2. Run linter: `ruff check services/ shared/` → exit 0
3. Run type checker: `mypy services/ shared/` → exit 0
4. Confirm CI passes on clean push to `phase-1-core-services` branch
5. Update `specs/status.md` — mark Phase 1 in progress, update progress %
