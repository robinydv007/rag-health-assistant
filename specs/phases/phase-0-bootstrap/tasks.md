# Phase 0 Tasks

> **Phase**: 0 — Bootstrap  
> **Status**: Not Started  
> **Progress**: 0 / 30

---

## Group 0 — Contracts & Schema

- [ ] Define `DocumentRecord` Pydantic model (`shared/models/document.py`)
- [ ] Define `QueryRecord` Pydantic model (`shared/models/query.py`)
- [ ] Define `ChunkMetadata` Pydantic model (`shared/models/chunk.py`)
- [ ] Define SQS 1/2/3 message schemas (`shared/models/messages.py`)
- [ ] Create Alembic setup + initial migration (documents, query_history, indexing_jobs, chunk_audit)
- [ ] Define Weaviate KnowledgeChunk schema (`shared/config/weaviate_schema.py`)
- [ ] Define shared settings module (`shared/config/settings.py`)

## Group 1 — Service Skeletons

- [ ] Scaffold Chat Service (`services/chat-service/src/main.py` + `/health` + `/ask` stub)
- [ ] Scaffold Uploader Service (`services/uploader-service/src/main.py` + `/health` + `/ingest` stub)
- [ ] Scaffold Doc Processing (`services/doc-processing/src/main.py` + SQS consumer loop)
- [ ] Scaffold Embedding Service (`services/embedding-service/src/main.py` + SQS consumer loop)
- [ ] Scaffold Indexing Service (`services/indexing-service/src/main.py` + SQS consumer loop)
- [ ] Scaffold Admin Service (`services/admin-service/src/main.py` + `/health` + `/admin/reindex` stub)

## Group 2 — Docker & Local Dev

- [ ] Write `Dockerfile` for each of the 6 services
- [ ] Write `docker-compose.yml` (all services + Weaviate + PostgreSQL + ElasticMQ + Adminer)
- [ ] Write `.env.example`
- [ ] Write `scripts/init-db.sh` (run Alembic migrations)
- [ ] Write `scripts/init-weaviate.sh` (create Weaviate schema)

## Group 3 — ADRs & Specs

- [ ] Write ADR 0001 — Microservices architecture
- [ ] Write ADR 0002 — SQS async pipeline
- [ ] Write ADR 0003 — BioGPT/SciBERT embeddings
- [ ] Write ADR 0004 — Zero-downtime re-index
- [ ] Write ADR 0005 — ECS Fargate over EKS

## Group 4 — Wiring & Integration

- [ ] Wire service configs to docker-compose
- [ ] Verify `docker-compose up --build` all services healthy
- [ ] Smoke test all 6 `/health` endpoints
- [ ] Run Alembic migrations on local PostgreSQL
- [ ] Create Weaviate schema on local Weaviate

## Group 5 — Verification

- [ ] Write unit tests for shared models
- [ ] Write unit tests for config module
- [ ] Write GitHub Actions CI workflow
- [ ] Confirm CI passes on clean branch
- [ ] Update `specs/status.md`
