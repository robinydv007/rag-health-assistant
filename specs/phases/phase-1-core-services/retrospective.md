# Phase 1 Retrospective — Core Services

> **Released**: 2026-05-13
> **Version**: v0.2.0
> **Branch**: `phase-1-core-services`
> **Duration**: 1 day (2026-05-12 brainstorm → 2026-05-13 complete)

---

## What Was Delivered

- **Uploader Service** — `POST /api/v1/knowledge/ingest`: multipart upload → MinIO → PostgreSQL → SQS 1, HTTP 202
- **Doc Processing Service** — SQS 1 consumer: Presidio PII scrub → PDF/DOCX/TXT parse → 512-token tiktoken chunks → SQS 2 publish → PG status update
- **Chat Service** — `POST /api/v1/knowledge/ask`: query expansion → Weaviate hybrid search → rerank → LLM call → JSON response + audit log; `GET /api/v1/knowledge/history`: paginated query history
- **Shared clients** — async S3/MinIO wrapper, OpenAI/Anthropic LLM client with provider fallback, medical synonym dictionary (150 entries)
- **78 unit tests** across 4 test suites; integration tests for all 3 services

---

## What Went Well

- **Group 0–3 implementations were clean** — all 44 tasks landed without rework on the service logic itself
- **Presidio ran fully locally** — zero AWS credentials needed for PII scrubbing in local dev
- **Provider fallback pattern** — LLM client primary/fallback design is already production-useful and required no re-work
- **tiktoken lazy-import pattern** — avoids BPE model download at container start; a subtle fix that made tests fast
- **Per-service PYTHONPATH isolation** — clean solution to the `src/` namespace collision between services

## What Didn't Go Well

- **Group 4 (Docker wiring) was deferred during initial implementation** — the "no network in sandbox" constraint meant the entire wiring group was left unchecked and discovered issues only at verification time
- **Three Docker bugs hit in sequence** during Group 4:
  1. `doc-processing` Dockerfile used `python src/main.py` (script mode) — relative imports broke
  2. `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` missing from `.env` — boto3 raised `NoCredentialsError` even for local ElasticMQ
  3. SQS queue URLs in `.env` used `localhost` hostname, not the Docker service name `elasticmq`
- **Audit log silent failure** — `query_history` writes were silently failing on every `/ask` call due to `:sources::jsonb` mixing SQLAlchemy named-parameter syntax with asyncpg positional syntax. The service returned HTTP 200 masking the failure — only caught during explicit DB verification in Group 4

## Lessons Learned

- **Group 4 should never be deferred** — wiring and smoke tests must run before marking Groups 1–3 complete; Docker integration bugs are invisible until the stack runs
- **Always verify audit log writes explicitly** — a service returning 200 with a silent `except` on an audit write satisfies no compliance requirement; verification must query the DB, not just check HTTP status
- **SQLAlchemy `text()` + asyncpg**: `::` PostgreSQL cast operator directly after a named parameter (`:param::type`) is not parsed correctly — use `CAST(:param AS type)` instead
- **Docker on Windows**: `sed -i` on bind-mounted files fails with "Resource busy" — redirect to `/tmp` instead

---

## Scope Changes

| Change | Direction | Tracking |
|--------|-----------|---------|
| `/ask` SSE streaming → JSON response | Reduced | ENH-006 (P3) in backlog |

---

## Bugs Found and Fixed During This Phase

| ID | Description | Fixed |
|----|-------------|-------|
| — | `doc-processing` Dockerfile CMD used script mode, broke relative imports | ✅ |
| — | Missing dummy AWS credentials for local boto3 | ✅ |
| — | SQS queue URLs used `localhost` instead of `elasticmq` inside Docker | ✅ |
| — | `weaviate-init` `sed -i` failed on Windows bind mount | ✅ |
| — | `query_history` audit write silently failed: `:sources::jsonb` asyncpg syntax error | ✅ |

---

## Verification Evidence

All commands run 2026-05-13 with the full docker-compose stack up.

### Health endpoints — all 6 services

```
$ curl -s http://localhost:8001/health
{"status":"healthy","service":"chat-service"}

$ curl -s http://localhost:8002/health
{"status":"healthy","service":"uploader-service"}

$ curl -s http://localhost:8006/api/v1/health
{"status":"healthy","service":"admin-service"}

$ docker logs docker-doc-processing-1 | tail -3
INFO:__main__:Doc Processing Service started — polling SQS 1
INFO:botocore.credentials:Found credentials in environment variables.
# (polling loop, no crash)

$ docker logs docker-embedding-service-1  # Phase 2 stub, sleeping
$ docker logs docker-indexing-service-1   # Phase 2 stub, sleeping
```

### AC-1 — POST /ingest

```
$ curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST http://localhost:8002/api/v1/knowledge/ingest \
    -F "file=@rag-healthcare\ requirement.pdf;type=application/pdf" \
    -F "title=RAG Healthcare Requirements" \
    -F "doc_type=clinical_guideline" \
    -F "uploaded_by=phase1-verifier"

{"job_id":"41de148a-830c-4428-8c06-d449cb797262","doc_id":"a568ba5c-0d74-4c22-a84a-132fcb21eb0a","status":"pending","status_url":"/api/v1/knowledge/history?doc_id=a568ba5c-0d74-4c22-a84a-132fcb21eb0a"}
HTTP_STATUS:202

# MinIO
[2026-05-13 08:27:37 UTC] 274KiB STANDARD rag-healthcare requirement.pdf

# PostgreSQL (captured immediately after upload — status=pending before doc-processing consumed it)
doc_id                               | status  | title                       | chunks_total
a568ba5c-0d74-4c22-a84a-132fcb21eb0a | pending | RAG Healthcare Requirements | (null)
```

Exit code: 202 ✓

### AC-2 — Doc Processing pipeline

```
$ docker logs docker-doc-processing-1 | grep a568ba5c
INFO:__main__:doc_id=a568ba5c-0d74-4c22-a84a-132fcb21eb0a processed: 11 chunks published to SQS 2

# PostgreSQL after processing
doc_id                               | status     | chunks_total
a568ba5c-0d74-4c22-a84a-132fcb21eb0a | processing | 11
```

Exit code: 0 ✓

### AC-3 — POST /ask

```
$ curl -s -X POST http://localhost:8001/api/v1/knowledge/ask \
    -H "Content-Type: application/json" \
    -d '{"question": "What is hypertension treatment?", "user_id": "phase1-verifier"}'

{"answer":"I'm sorry, but the provided sources do not contain information on the treatment of hypertension.","sources":[]}
HTTP_STATUS:200
```

Exit code: 200 ✓

### AC-4 — query_history audit log

```
$ psql -c "SELECT query_id, user_id, question, model_used, latency_ms FROM query_history ORDER BY created_at DESC LIMIT 1;"

               query_id               |     user_id     |            question             | model_used | latency_ms
--------------------------------------+-----------------+---------------------------------+------------+------------
 1443282a-94a0-48bb-a605-c3d5205c2341 | phase1-verifier | What is hypertension treatment? | mock       |       4673
(1 row)
```

Exit code: 0 ✓

### AC-5 — GET /history

```
$ curl -s "http://localhost:8001/api/v1/knowledge/history?user_id=phase1-verifier&limit=5&offset=0"

{
  "queries": [
    {
      "query_id": "1443282a-94a0-48bb-a605-c3d5205c2341",
      "user_id": "phase1-verifier",
      "session_id": null,
      "question": "What is hypertension treatment?",
      "response": "I'm sorry, but the provided sources do not contain information on the treatment of hypertension.",
      "sources": [],
      "model_used": "mock",
      "latency_ms": 4673,
      "index_queried": "live",
      "pii_detected": false,
      "created_at": "2026-05-13T08:30:53.462411+00:00"
    }
  ],
  "total": 1,
  "limit": 5,
  "offset": 0
}
HTTP_STATUS:200
```

Exit code: 200 ✓

### AC-6 — Unit tests (78 total)

```
$ MSYS_NO_PATHCONV=1 docker run --rm -v "D:/Development/Projects/ai/rag-health-assistant:/app" -w //app python:3.11-slim \
    sh -c "pip install -q pytest pytest-asyncio httpx \
             -r services/doc-processing/requirements.txt \
             -r services/chat-service/requirements.txt \
             -r services/uploader-service/requirements.txt && \
           pytest tests/ -q && \
           PYTHONPATH=services/doc-processing pytest services/doc-processing/tests/ -q -m 'not integration' && \
           PYTHONPATH=services/chat-service pytest services/chat-service/tests/ -q -m 'not integration' && \
           PYTHONPATH=services/uploader-service pytest services/uploader-service/tests/ -q -m 'not integration'"

=== shared ===    15 passed in 0.50s
=== doc-processing ===    33 passed, 1 deselected in 3.06s
=== chat-service ===    20 passed, 1 deselected in 2.31s
=== uploader-service ===    10 passed, 1 deselected in 1.57s
```

Exit code: 0 ✓  Total: **78 unit tests passed**

### ruff check

```
$ ruff check .
All checks passed!
```

Exit code: 0 ✓

### mypy

```
$ mypy shared/ --ignore-missing-imports
Success: no issues found in 14 source files
```

Exit code: 0 ✓
