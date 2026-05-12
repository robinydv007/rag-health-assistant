# Phase 0 — Bootstrap

> **Status**: Not Started  
> **Version**: v0.1.0  
> **Goal**: Working local development environment with all service skeletons, shared contracts locked, and CI pipeline passing.

---

## Objective

Stand up the complete project foundation so every engineer can clone, run `docker-compose up`, and have a working local stack. Lock the shared contracts (Pydantic models, SQS schemas, config) so Phase 1 service implementation can proceed in parallel across teams.

This phase produces **no user-facing features** — it produces the scaffolding that makes all future features possible.

---

## Scope

### In
- All 6 service directories with FastAPI/Python boilerplate (routes, health endpoint, config)
- Shared library: Pydantic models, SQS message schemas, config module, LLM Router stub
- `docker-compose.yml`: all services + Weaviate + PostgreSQL + local SQS (ElasticMQ)
- GitHub Actions CI: ruff lint, mypy type check, pytest unit tests on every PR
- PostgreSQL schema migrations (Alembic)
- 4+ ADRs for core design decisions
- `CLAUDE.md` project rules
- All spec documents populated

### Out
- Real AWS infrastructure
- Real LLM API calls (use mock)
- Real BioGPT/SciBERT embeddings (use random vectors)
- Any user-facing functionality beyond `/health` endpoints

---

## Success Criteria

- [ ] `docker-compose up` brings all services online — all `/health` endpoints return 200
- [ ] Shared Pydantic models importable across services with no import errors
- [ ] CI passes (lint + type check + tests) on a clean branch
- [ ] All 4 ADRs written and reviewed
- [ ] PostgreSQL schema created and migrated via Alembic
- [ ] Weaviate schema (KnowledgeChunk class) created on startup
- [ ] All spec documents complete (no `TBD` in charter, roadmap, success-criteria)

---

## Non-Goals

- Production-quality error handling in services (defer to Phase 1+)
- Performance optimization
- Security hardening (defer to Phase 5)
- Real cloud deployment
