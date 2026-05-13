# Phase 2 — Embedding & Indexing

> **Version**: 1.0
> **Status**: In Progress
> **Branch**: `phase-2-embedding-indexing`
> **Follows**: Phase 1 — Core Services

---

## Goal

The full document pipeline runs end-to-end with real BiomedBERT embeddings stored in Weaviate.
A document uploaded in Phase 1 becomes semantically queryable — `/ask` returns relevant chunks
instead of noise from placeholder zero-vectors.

---

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Embedding model | `BiomedNLP-BiomedBERT` via HuggingFace Serverless Inference API | Medical-domain-specific, API-callable, no GPU hosting required |
| Provider abstraction | `EMBEDDING_PROVIDER` env var (`hf_inference` \| `http_endpoint`) | Self-hosted GPU switch requires only an env var change — zero code changes |
| EC2 GPU instance | Removed | HF API replaces it; ADR 0003 amended accordingly |
| Batch size | 64 chunks per HF API call | HF Inference API supports batched inputs; matches original throughput target |
| DLQ alerting | Alert logic + local webhook hook | Real CloudWatch/SNS wired in Phase 5 with production infra |
| Search eval set | Deferred to Phase 3 | Phase 3 needs it for LLM router optimization |
| HL7 parsing | Still deferred to Phase 3 | Keep Phase 2 focused on embedding pipeline |
| Indexing Coordinator | Sub-component of Indexing Service | Not a separate service; tracks chunk completion via PG counters |

---

## Scope

### In Scope

- **Embedding Service** (`services/embedding-service/`): SQS 2 consumer → batch 64 chunks → HF BiomedBERT API → SQS 3 publish → `documents.status = embedding`
- **Indexing Service** (`services/indexing-service/`): SQS 3 consumer → Weaviate `KnowledgeChunk` write → `documents.chunks_indexed++` → `chunk_audit` row → `status = indexed` when complete
- **Indexing Coordinator** (sub-component of Indexing Service): when `chunks_indexed == chunks_total` → set `documents.status = indexed`
- **DLQ monitor** (`shared/utils/dlq_monitor.py`): depth check + log + optional webhook on depth > 0 via `DLQ_ALERT_WEBHOOK_URL`
- **Chat Service update**: replace 768-dim zero-vector with real BiomedBERT embedding call in `searcher.py`
- **Shared embedding client** (`shared/clients/embedding_client.py`): provider abstraction — `HFInferenceClient` + `HTTPEndpointClient`
- **ADR 0003 amendment**: BiomedBERT via HF Inference API replaces self-hosted BioGPT/SciBERT on EC2 GPU
- **SQS 3 + DLQ 3** added to docker-compose
- **Alembic migrations**: `chunk_audit` table (new); verify `indexing_jobs` migration exists
- **End-to-end integration test**: upload PDF → indexed in Weaviate → `/ask` returns relevant chunk

### Out of Scope

- HL7/EHR parsing (Phase 3)
- Real CloudWatch/SNS alerting (Phase 5)
- Search relevance evaluation set (Phase 3)
- LLM Router with circuit breaker (Phase 3)
- Admin Service re-index flow (Phase 3)
- EC2 GPU provisioning (removed from project)
- HuggingFace Dedicated Endpoint provisioning (Phase 5 with prod infra)

---

## Deliverables

| Deliverable | Verification command |
|-------------|---------------------|
| Embedding Service running | `curl http://localhost:{port}/health` → HTTP 200 |
| SQS 2 → SQS 3 pipeline | SQS 2 message → SQS 3 message with 768-dim float array per chunk |
| Weaviate `KnowledgeChunk` written | Weaviate query returns object with `embeddedModel = "BiomedBERT"` |
| `documents.status = indexed` | `SELECT status FROM documents WHERE doc_id=...` → `indexed` |
| `chunk_audit` rows written | `SELECT count(*) FROM chunk_audit WHERE doc_id=...` matches `chunks_total` |
| Real query embedding in `/ask` | Weaviate hybrid search uses non-zero 768-dim vector from BiomedBERT |
| DLQ alert fires | Set DLQ depth > 0 → log warning + webhook POSTed (if URL configured) |
| All unit + integration tests pass | `pytest services/ shared/ -v` exits 0 |
| Lint and type checks | `ruff check services/ shared/` and `mypy shared/ --ignore-missing-imports` exit 0 |
| CI | GitHub Actions passes on clean push to `phase-2-embedding-indexing` branch |

---

## Acceptance Criteria

1. SQS 2 message with chunks → Embedding Service calls HF BiomedBERT API → SQS 3 message contains a 768-dim float array for each chunk
2. SQS 3 message → Indexing Service writes `KnowledgeChunk` to Weaviate with correct properties; `documents.chunks_indexed` incremented; `chunk_audit` row written with `embedded_model = "BiomedBERT"`
3. When `chunks_indexed == chunks_total` for a document → `documents.status = indexed`
4. `POST /ask` with a question → Weaviate hybrid search uses real BiomedBERT embedding (non-zero vector) → JSON response contains semantically relevant chunks in `sources`
5. DLQ depth > 0 on any queue → alert logged; if `DLQ_ALERT_WEBHOOK_URL` is set, webhook POSTed with queue name and depth
6. All unit tests and integration tests pass (`pytest services/ shared/ -v` exits 0)
7. CI pipeline passes on a clean push to `phase-2-embedding-indexing` branch
