# Phase 0 Tasks

> **Phase**: 0 — Bootstrap  
> **Status**: In Progress  
> **Progress**: 29 / 35

---

## Group 0 — Contracts & Schema

- [x] Define `DocumentRecord` Pydantic model (`shared/models/document.py`)
- [x] Define `QueryRecord` Pydantic model (`shared/models/query.py`)
- [x] Define `ChunkMetadata` Pydantic model (`shared/models/chunk.py`)
- [x] Define SQS 1/2/3 message schemas (`shared/models/messages.py`)
- [x] Create Alembic setup + initial migration (documents, query_history, indexing_jobs, chunk_audit)
- [x] Define Weaviate KnowledgeChunk schema (`shared/config/weaviate_schema.py`)
- [x] Define shared settings module (`shared/config/settings.py`)

## Group 1 — Service Skeletons

- [x] Scaffold Chat Service (`services/chat-service/src/main.py` + `/health` + `/ask` stub)
- [x] Scaffold Uploader Service (`services/uploader-service/src/main.py` + `/health` + `/ingest` stub)
- [x] Scaffold Doc Processing (`services/doc-processing/src/main.py` + SQS consumer loop)
- [x] Scaffold Embedding Service (`services/embedding-service/src/main.py` + SQS consumer loop)
- [x] Scaffold Indexing Service (`services/indexing-service/src/main.py` + SQS consumer loop)
- [x] Scaffold Admin Service (`services/admin-service/src/main.py` + `/health` + `/admin/reindex` stub)

## Group 2 — Docker & Local Dev

- [x] Write `Dockerfile` for each of the 6 services
- [x] Write `docker-compose.yml` (all services + Weaviate + PostgreSQL + ElasticMQ + Adminer)
- [x] Write `.env.example`
- [x] Write `scripts/init-db.sh` (run Alembic migrations)
- [x] Write `scripts/init-weaviate.sh` (create Weaviate schema)

## Group 3 — ADRs & Specs

- [x] Write ADR 0001 — Microservices architecture
- [x] Write ADR 0002 — SQS async pipeline
- [x] Write ADR 0003 — BioGPT/SciBERT embeddings
- [x] Write ADR 0004 — Zero-downtime re-index
- [x] Write ADR 0005 — ECS Fargate over EKS
- [x] Write ADR 0006 — Vector DB: Weaviate (hybrid search, self-hosted, alias pattern)
- [x] Write ADR 0007 — Backend framework: FastAPI (async SSE, Pydantic, ML ecosystem)

## Group 4 — Wiring & Integration

- [ ] Wire service configs to docker-compose
- [ ] Verify `docker-compose up --build` all services healthy
- [ ] Smoke test all 6 `/health` endpoints
- [ ] Run Alembic migrations on local PostgreSQL
- [ ] Create Weaviate schema on local Weaviate

## Group 5 — Verification

- [x] Write unit tests for shared models
- [x] Write unit tests for config module
- [x] Write GitHub Actions CI workflow
- [ ] Confirm CI passes on clean branch
- [ ] Update `specs/status.md`
