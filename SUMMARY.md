# RAG Healthcare Knowledge Assistant — Project Summary

## What It Does

An internal AI assistant for healthcare teams. Staff ask natural-language medical questions and receive accurate, source-cited answers drawn from the organisation's own clinical document library — clinical guidelines, hospital policies, HL7 standards, drug formularies.

- Accepts document uploads (PDF, DOCX, TXT, HL7) and processes them through a 3-stage async pipeline
- Embeds document chunks and stores them in a hybrid vector + keyword index
- Answers queries using retrieval-augmented generation with full source citations and a HIPAA-compliant audit trail

---

## Architecture Highlights

6 microservices behind AWS API Gateway, communicating through SQS queues — no service waits on another:

```
[ Uploader ] → SQS 1 → [ Doc Processing ] → SQS 2 → [ Embedding ] → SQS 3 → [ Indexing ]
                                                                                     ↓
[ Chat Service ] ←————————————————————————————————————————————————————————— [ Weaviate ]
```

- **Async pipeline** — each service finishes its job and pushes to the next queue; failures go to DLQs with alerting
- **Hybrid search** — Weaviate combines dense vector similarity (semantic) with BM25 (keyword) for better retrieval
- **Zero-downtime re-indexing** — shadow index built in the background, alias swapped atomically when ready
- **HIPAA compliance** — PII/PHI scrubbed in Doc Processing before any downstream service; every query written to `query_history` audit log

---

## Key Design Decisions

| ADR | Decision | Rationale |
|-----|----------|-----------|
| 0001 | Microservices over monolith | Independent scaling; each stage (ingest, embed, index) has different compute needs |
| 0002 | SQS async pipeline with DLQs | Decoupled failure domains; SQS DLQs give built-in retry and poison-message isolation |
| 0003a | OpenAI text-embedding-3-large (3072-dim) | HF BiomedBERT not production-ready; provider-swappable via `EMBEDDING_PROVIDER` env var |
| 0004 | Shadow index + alias swap | Re-indexing without downtime; live traffic hits the alias, not the index directly |
| 0005 | ECS Fargate over EKS | Lower operational overhead; Fargate handles scaling without cluster management |
| 0006 | Weaviate for vector DB | Native hybrid search (dense + BM25), self-hosted, supports alias-based index swap |
| 0007 | FastAPI for all HTTP services | Async-native, SSE-ready, Pydantic validation, strong ML ecosystem fit |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python FastAPI |
| LLM (primary) | OpenAI GPT-4o |
| LLM (fallback) | Anthropic Claude (claude-sonnet-4-6) |
| Embeddings | OpenAI text-embedding-3-large |
| Vector DB | Weaviate (hybrid search) |
| SQL DB | PostgreSQL — audit logs, doc status, query history |
| Queues | AWS SQS + ElasticMQ (local) |
| Storage | AWS S3 + MinIO (local) |
| Compute | ECS Fargate + EC2 GPU (embeddings) |
| CI/CD | GitHub Actions |

---

## Performance Targets

| Metric | Target |
|--------|--------|
| p95 response time | < 2 seconds |
| Concurrent users | 500+ |
| Document throughput | 1,000+ docs/min during re-index |
| Uptime | 99.9% |
| Re-index downtime | Zero |

---

## How to Run

```bash
cp .env.example .env          # add OpenAI key, or set EMBEDDING_PROVIDER=mock for keyless mode
docker compose -f infrastructure/docker/docker-compose.yml up --build
curl -X POST http://localhost:8002/api/v1/knowledge/ingest \
  -F "file=@document.pdf" -F "title=Test" -F "doc_type=clinical_guideline"
curl -X POST http://localhost:8001/api/v1/knowledge/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the discharge protocol?", "user_id": "usr_001", "session_id": "sess_001"}'
```

Full setup → [README.md](README.md) · API reference → [specs/architecture/api-reference.md](specs/architecture/api-reference.md)
