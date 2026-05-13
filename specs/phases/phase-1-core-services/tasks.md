# Phase 1 Tasks

> **Phase**: 1 — Core Services
> **Status**: Complete
> **Progress**: 47 / 47

---

## Group 0 — Infrastructure & Shared Prerequisites

- [x] Add MinIO service to `docker-compose.yml` (image, port 9000/9001, bucket auto-create)
- [x] Create `shared/clients/s3_client.py` — boto3 wrapper, endpoint via `S3_ENDPOINT_URL`
- [x] Create `shared/clients/llm_client.py` — async OpenAI/Anthropic streaming, `LLM_PROVIDER` + `LLM_MOCK` env vars
- [x] Create `shared/data/medical_synonyms.yaml` (150 entries)
- [x] Create `shared/utils/query_expander.py`
- [x] Add Phase 1 deps to service `requirements.txt` files: `openai`, `anthropic`, `tiktoken`, `weaviate-client`, `pyyaml`
- [x] Update `.env.example` with new vars

## Group 1 — Uploader Service

- [x] Implement `POST /api/v1/knowledge/ingest` handler (file validation, S3 upload, PG insert, SQS 1 publish, 202 response)
- [x] Add async SQLAlchemy session factory (`services/uploader-service/src/db.py`)
- [x] Unit test: valid PDF upload → HTTP 202
- [x] Unit test: invalid file type → HTTP 422
- [x] Unit test: S3 upload failure → HTTP 500
- [x] Unit test: PG insert failure → HTTP 500
- [x] Integration test: real MinIO + PostgreSQL — verify all side effects

## Group 2 — Doc Processing Service

- [x] Implement SQS 1 consumer loop (long-poll, dispatch, delete on success, PG update)
- [x] Implement Presidio PII scrubber (`services/doc-processing/src/scrubber.py`)
- [x] Implement PDF parser (`services/doc-processing/src/parsers/pdf_parser.py`)
- [x] Implement DOCX parser (`services/doc-processing/src/parsers/docx_parser.py`)
- [x] Implement TXT parser (`services/doc-processing/src/parsers/txt_parser.py`)
- [x] Implement chunker: 512-token chunks, 50-token overlap (`services/doc-processing/src/chunker.py`)
- [x] Publish chunk batch to SQS 2; update `documents.chunks_total`
- [x] Unit test: PII scrubber (verify all entity types redacted)
- [x] Unit test: PDF parser (fixture file, verify text + page_num)
- [x] Unit test: DOCX parser (fixture file)
- [x] Unit test: TXT parser (UTF-8 and latin-1 fixtures)
- [x] Unit test: chunker (token counts ≤512, overlap ≥50 between adjacent chunks)
- [x] Integration test: SQS 1 message → SQS 2 messages appear + PG status = processing + no raw PII in chunks

## Group 3 — Chat Service

- [x] Implement query expander (`services/chat-service/src/expander.py`)
- [x] Implement Weaviate hybrid searcher (`services/chat-service/src/searcher.py`)
- [x] Implement score-based reranker (`services/chat-service/src/reranker.py`)
- [x] Implement LLM caller with SSE streaming (`services/chat-service/src/llm_caller.py`)
- [x] Implement `POST /api/v1/knowledge/ask` endpoint
- [x] Implement `GET /api/v1/knowledge/history` endpoint
- [x] Unit test: query expander
- [x] Unit test: searcher (mock Weaviate)
- [x] Unit test: reranker
- [x] Unit test: audit log write (success and error paths)
- [x] Integration test: `/ask` end-to-end with mock LLM + seeded Weaviate fixture

## Group 4 — Wiring & Integration

- [x] Verify `docker-compose up --build` — all services healthy including MinIO
- [x] End-to-end upload test: PDF → MinIO object + PG row + SQS 1 message
- [x] End-to-end doc processing test: SQS 1 → SQS 2 chunks + PG status = processing
- [x] End-to-end ask test: seeded Weaviate → JSON response completes → `query_history` row written
- [x] Smoke test all 6 `/health` endpoints → HTTP 200

## Group 5 — Verification

- [x] `pytest services/ shared/ -v --tb=short` → unit tests pass (per-service invocation; integration tests require Docker)
- [x] `ruff check services/ shared/` → exit 0
- [x] `mypy shared/ --ignore-missing-imports` → exit 0 (14 source files, no issues)
- [x] CI passes on clean push to `phase-1-core-services` branch
- [x] Update `specs/status.md`
