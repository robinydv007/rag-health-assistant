# Phase 0 — Execution Plan

> **Execution Order**: Group 0 → (Groups 1 + 2 + 3 in parallel) → Group 4 → Group 5

---

## Group 0 — Contracts & Schema (Sequential — blocks everything)

**Sequential.** No external dependencies beyond Python + PostgreSQL.  
**Commit**: `feat(contracts): define shared Pydantic models, SQS schemas, and DB migrations`

Tasks:
- [ ] Define shared Pydantic models in `shared/models/`
  - `DocumentRecord`, `QueryRecord`, `ChunkMetadata`, `SQSMessage` variants
- [ ] Define SQS message schemas (SQS 1, 2, 3 payloads)
- [ ] Write PostgreSQL migrations (Alembic): `documents`, `query_history`, `indexing_jobs`, `chunk_audit`
- [ ] Define Weaviate schema (`KnowledgeChunk` class) in `shared/config/weaviate_schema.py`
- [ ] Define shared config module (`shared/config/settings.py` — pydantic-settings)

---

## Group 1 — Service Skeletons (Parallel with Groups 2 + 3)

**Parallel with Groups 2 and 3.**  
**Dependencies**: Group 0 contracts.  
**Commit**: `feat(services): scaffold all 6 service FastAPI apps with health endpoints`

Tasks:
- [ ] Chat Service skeleton: FastAPI app, `/health`, `/ask` stub (returns mock response), config wired
- [ ] Uploader Service skeleton: FastAPI app, `/health`, `/ingest` stub (returns 202 mock), config wired
- [ ] Doc Processing skeleton: SQS consumer loop, message handler stub, config wired
- [ ] Embedding Service skeleton: SQS consumer loop, batch handler stub (returns random vectors), config wired
- [ ] Indexing Service skeleton: SQS consumer loop, index writer stub, config wired
- [ ] Admin Service skeleton: FastAPI app, `/health`, `/admin/reindex` stub, config wired

---

## Group 2 — Docker & Local Dev (Parallel with Groups 1 + 3)

**Parallel with Groups 1 and 3.**  
**Dependencies**: Group 0 contracts (for Dockerfile base image consistency).  
**Commit**: `infra(docker): docker-compose with all services, Weaviate, PostgreSQL, ElasticMQ`

Tasks:
- [ ] Write `Dockerfile` for each service (Python 3.11-slim, multi-stage)
- [ ] Write `docker-compose.yml`:
  - All 6 services
  - Weaviate (latest)
  - PostgreSQL 15
  - ElasticMQ (local SQS)
  - Adminer (DB GUI for dev)
- [ ] Write `.env.example` with all required env vars
- [ ] Write `scripts/init-db.sh` to run Alembic migrations on startup
- [ ] Write `scripts/init-weaviate.sh` to create Weaviate schema on startup

---

## Group 3 — ADRs & Specs (Parallel with Groups 1 + 2)

**Parallel with Groups 1 and 2.**  
**Dependencies**: None.  
**Commit**: `docs: write ADRs 0001–0005 and complete all spec documents`

Tasks:
- [ ] ADR 0001: Microservices over monolith
- [ ] ADR 0002: SQS async pipeline
- [ ] ADR 0003: BioGPT/SciBERT for medical embeddings
- [ ] ADR 0004: Zero-downtime re-index via shadow index
- [ ] ADR 0005: ECS Fargate over EKS
- [ ] Complete `specs/status.md`
- [ ] Complete `specs/backlog/backlog.md` with initial features

---

## Group 4 — Wiring & Integration (Sequential — after Groups 1 + 2 + 3)

**Sequential.**  
**Dependencies**: All of Groups 1, 2, 3.  
**Commit**: `feat(integration): wire services into docker-compose, validate startup`

Tasks:
- [ ] Connect service configs to docker-compose env vars
- [ ] Wire shared library imports into each service
- [ ] Verify `docker-compose up --build` brings all 7 containers healthy
- [ ] Smoke test: `curl http://localhost:8001/health` → 200 for each service
- [ ] Run Alembic migrations against local PostgreSQL
- [ ] Create Weaviate schema against local Weaviate

---

## Group 5 — Verification (Sequential — last)

**Sequential.**  
**Dependencies**: Group 4 (full stack running).  
**Commit**: `chore(ci): GitHub Actions pipeline with lint, type check, and unit tests`

Tasks:
- [ ] Write unit tests for shared models (test serialization / validation)
- [ ] Write unit test for config module (test env var loading)
- [ ] Write GitHub Actions workflow (`.github/workflows/ci.yml`):
  - `ruff check .`
  - `mypy services/ shared/`
  - `pytest tests/ -v`
- [ ] Confirm CI passes on a clean branch
- [ ] Update `specs/status.md` to reflect phase completion
