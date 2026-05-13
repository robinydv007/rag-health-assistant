# Phase 2 Retrospective — Embedding & Indexing

> **Phase**: 2 — Embedding & Indexing
> **Version**: v0.3.0
> **Branch**: `phase-2-embedding-indexing`
> **Completed**: 2026-05-13

---

## What Was Delivered

- **Embedding Service**: SQS 2 consumer → Batcher (64 chunks / 10 s timeout) → OpenAI `text-embedding-3-large` → SQS 3 publisher → PG `status=embedding`
- **Indexing Service**: SQS 3 consumer → Weaviate `KnowledgeChunk` upsert (UUID5 idempotent) → `chunk_audit` row → PG `chunks_indexed++` → `status=indexed` when complete
- **Indexing Coordinator**: inline completion check — sets `documents.status=indexed` when `chunks_indexed == chunks_total`
- **DLQ Monitor**: shared utility, 60s poll, log WARNING + optional HTTP webhook; wired as background task in Indexing Service
- **Chat Service update**: real OpenAI 3072-dim query embedding replaces zero-vector in hybrid search
- **Shared EmbeddingClient**: `OpenAIEmbeddingClient` + `HTTPEndpointClient` + `MockEmbeddingClient` behind `get_embedding_client()` factory (ENH-007)
- **End-to-end verified**: PDF upload → `status=indexed` (11/11 chunks) + Weaviate queryable + `/ask` returns semantically relevant chunks with sources

---

## What Went Well

- **Pipeline correctness on first run**: The full SQS 1→2→3→Weaviate chain worked end-to-end on the first Docker stack test. No message routing bugs.
- **Idempotent Weaviate upsert**: UUID5 from `chunk_id` means re-processing a document is safe — no duplicate objects.
- **Provider abstraction pays off immediately**: The HF→OpenAI switch mid-phase required only swapping `HFInferenceClient` for `OpenAIEmbeddingClient` — zero changes in Embedding Service consumer logic or Chat Service searcher.
- **DLQ monitor as shared util**: Reusable across all services from day one; will serve Phase 3 and 4 without modification.
- **ENH-007 (mock mode)**: Unblocks any developer without API keys from running the full stack locally — delivered earlier than planned (Phase 3) because it was low-effort and high-value.

---

## What Didn't Go Well

- **HuggingFace BiomedBERT failed**: The original Phase 2 plan used BiomedBERT via HF Serverless API. It returned HTTP 400 on all batched embedding requests. Lost time diagnosing before pivoting to OpenAI. The HF Serverless API is not production-ready for embedding workloads.
- **Weaviate client re-instantiated per chunk**: `WeaviateWriter.upsert` opened a new connection per chunk — 3 extra HTTP calls each (PyPI version check + openid probe + meta handshake). Caught late in the phase from log observation. Fixed: persistent connection in `__init__`.
- **Content-type trust bug in uploader**: `file.content_type` from the HTTP client header was trusted blindly. A `.docx` uploaded with `Content-Type: application/pdf` crashed the PDF parser. Fixed: magic-byte sniffing after `file.read()`.
- **`__init__.py` files accidentally deleted**: `services/embedding-service/tests/__init__.py` and `services/indexing-service/tests/__init__.py` were deleted at some point, causing namespace collision in pytest collection. Restored during `/complete-phase` verification.
- **Test assertion bug in shared tests**: `test_mock_clients.py` asserted `"no API key" in full_response.lower()` — mixed-case search string against lowercased string always fails. Fixed: `"no api key"`.

---

## Lessons Learned

1. **Verify third-party API readiness before committing to it in a phase plan.** HF Serverless Inference was listed as the primary embedding provider in the spec without a prior integration test. A 15-minute spike against the real API would have caught the HTTP 400 issue before planning.
2. **Log inspection catches architectural waste early.** The per-chunk Weaviate reconnect was invisible in tests (mocked client) but obvious in Docker logs. Log review should be part of the integration-test checklist, not an afterthought.
3. **Magic-byte sniffing belongs in any file upload endpoint.** HTTP clients are unreliable about `Content-Type`. This is a standard hardening step — add it to the project template.
4. **`__init__.py` in test directories is load-bearing** when multiple services share a `src` module name. Deleting them silently breaks cross-service collection in pytest. Document this in the developer guide.

---

## Bugs Fixed During Phase

| Fix | Description |
|-----|-------------|
| `fix(uploader)` | Magic-byte sniffing replaces trusting `Content-Type` header |
| `fix(indexing)` | Persistent Weaviate client — connect once, reuse across all chunks |
| `fix(tests)` | `test_mock_clients.py` case-insensitive assertion corrected |
| `fix(tests)` | Restored deleted `__init__.py` in embedding/indexing test dirs |

---

## Metrics

| Metric | Value |
|--------|-------|
| Unit tests added this phase | 57 (embedding: 10, indexing: 12, chat: 20, shared: 15) |
| Total unit tests (project) | 135 |
| Services added | 2 (embedding-service, indexing-service) |
| Weaviate chunks indexed (e2e test) | 11 / 11 |
| Ruff violations | 0 |
| mypy errors | 0 |
| Docker containers healthy | 8 / 8 |

---

## Verification Evidence

All commands run fresh during `/complete-phase` on 2026-05-13 against the live stack.

### End-to-End: Upload test
```
POST http://localhost:8002/api/v1/knowledge/ingest  (rag-healthcare requirement.pdf)
→ HTTP 202
{"job_id":"8f9e71c8-3282-4dca-a79f-cb1f4e42a392","doc_id":"f907f1a4-8596-43eb-9966-02a6e475df3a","status":"pending","status_url":"/api/v1/knowledge/history?doc_id=f907f1a4-8596-43eb-9966-02a6e475df3a"}
EXIT: 0
```

### End-to-End: PG status=indexed + chunks
```sql
SELECT doc_id, status, chunks_total, chunks_indexed
FROM documents WHERE doc_id='f907f1a4-8596-43eb-9966-02a6e475df3a';
→  status=indexed  chunks_total=11  chunks_indexed=11
EXIT: 0
```

### End-to-End: chunk_audit rows
```sql
SELECT count(*) AS audit_rows FROM chunk_audit
WHERE doc_id='f907f1a4-8596-43eb-9966-02a6e475df3a';
→  audit_rows=11
EXIT: 0
```

### End-to-End: Weaviate KnowledgeChunk objects
```
POST http://localhost:8080/v1/graphql
Query: Get{KnowledgeChunk(where:{docId="f907f1a4..."},limit:3){docId chunkId embeddedModel title}}
→ 3 objects returned, embeddedModel="text-embedding-3-large", title="RAG Healthcare Requirements"
EXIT: 0
```

### End-to-End: /ask returns relevant chunks
```
POST http://localhost:8001/api/v1/knowledge/ask
{"question":"What are the key requirements for a RAG healthcare assistant?","user_id":"e2e-test","index":"live"}
→ HTTP 200, answer with 3 sources from doc_id=f907f1a4..., pages 1/2/10
EXIT: 0
```

### pytest — doc-processing unit tests (33 tests)
```
PYTHONPATH=services/doc-processing python -m pytest \
  services/doc-processing/tests/test_scrubber.py \
  services/doc-processing/tests/test_pdf_parser.py \
  services/doc-processing/tests/test_docx_parser.py \
  services/doc-processing/tests/test_txt_parser.py \
  services/doc-processing/tests/test_chunker.py \
  -v --tb=short -m "not integration"
→ 33 passed in 4.08s
EXIT: 0
```

### pytest — chat-service unit tests (20 tests)
```
PYTHONPATH=services/chat-service python -m pytest \
  services/chat-service/tests/test_expander.py \
  services/chat-service/tests/test_searcher.py \
  services/chat-service/tests/test_reranker.py \
  services/chat-service/tests/test_audit_log.py \
  -v --tb=short -m "not integration"
→ 20 passed, 1 warning in 1.80s
EXIT: 0
```

### pytest — embedding-service unit tests (10 tests)
```
PYTHONPATH=services/embedding-service python -m pytest \
  services/embedding-service/tests/test_batcher.py \
  services/embedding-service/tests/test_embedding_client.py \
  services/embedding-service/tests/test_publisher.py \
  -v --tb=short -m "not integration"
→ 10 passed in 1.66s
EXIT: 0
```

### pytest — indexing-service unit tests (12 tests)
```
PYTHONPATH=services/indexing-service python -m pytest \
  services/indexing-service/tests/test_weaviate_writer.py \
  services/indexing-service/tests/test_coordinator.py \
  services/indexing-service/tests/test_dlq_monitor.py \
  -v --tb=short -m "not integration"
→ 12 passed in 1.83s
EXIT: 0
```

### pytest — uploader-service unit tests (10 tests)
```
PYTHONPATH=services/uploader-service python -m pytest \
  services/uploader-service/tests/test_ingest.py \
  -v --tb=short -m "not integration"
→ 10 passed in 1.30s
EXIT: 0
```

### pytest — shared tests (19 tests)
```
python -m pytest tests/ -v --tb=short -m "not integration"
→ 19 passed in 0.12s
EXIT: 0
```

### ruff check
```
ruff check services/ shared/
→ All checks passed!
EXIT: 0
```

### mypy
```
mypy shared/ --ignore-missing-imports
→ Success: no issues found in 16 source files
EXIT: 0
```
