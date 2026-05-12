# Phase 0 History

> Append-only decision log. Format: `### [TYPE] YYYY-MM-DD — Title`

---

### [NOTE] 2026-05-12 — Project initialized from architecture design

Topics: project-init, architecture, scope
Affects-phases: phase-0-bootstrap
Affects-specs: specs/architecture/overview.md, specs/vision/project-charter.md
Detail: Project scaffolded from ARCHITECTURE.md (v1.0) and architecture-diagram.png. Architecture was pre-designed by the Technical Lead. Phase 0 scope locked to bootstrapping the dev environment and contracts — no user-facing features. All spec documents populated from the architecture doc.

---

### [DECISION] 2026-05-12 — Monorepo structure chosen for all 6 services

Topics: monorepo, services, repository-structure
Affects-phases: all
Affects-specs: specs/architecture/overview.md
Detail: All 6 microservices live in a single Git repository under `services/`. Shared library lives in `shared/`. This simplifies contract changes (shared models updated in one PR), cross-service integration tests, and CI pipeline configuration. Trade-off: larger repo, but the services are tightly coupled by contract and will be versioned together.

---

### [DECISION] 2026-05-12 — Python 3.11 + FastAPI + pydantic-settings as baseline

Topics: tech-stack, python, fastapi
Affects-phases: phase-0-bootstrap
Affects-specs: specs/architecture/overview.md
Detail: FastAPI chosen for async support, native SSE (for Chat Service streaming), pydantic integration, and strong ML ecosystem. Python 3.11 for performance improvements and better error messages. pydantic-settings for typed, validated environment config across all services.

---

### [DECISION] 2026-05-12 — ElasticMQ as local SQS replacement in docker-compose

Topics: local-dev, sqs, elasticmq
Affects-phases: phase-0-bootstrap
Affects-specs: none
Detail: ElasticMQ is an SQS-compatible server that runs locally in Docker. This lets the full async pipeline work in docker-compose without real AWS credentials. The boto3 SQS client is pointed at `http://elasticmq:9324` in local dev and at real SQS endpoint in staging/prod via environment config.

---

### [NOTE] 2026-05-12 — Phase 0 formally started; pre-phase scaffold work accounted for

Topics: project-init, local-dev, bootstrap, contracts
Affects-phases: phase-0-bootstrap
Affects-specs: specs/status.md, specs/phases/phase-0-bootstrap/tasks.md
Detail: Phase formally opened via `/start-phase`. A readiness review identified that significant scaffold work had been completed before the phase was formally started: `shared/config/settings.py`, `shared/config/weaviate_schema.py`, `docker-compose.yml`, `.env.example`, all 6 service health-endpoint skeletons, and ADRs 0001–0007. Tasks.md updated to reflect actual state (11/35 done, 6 in-progress). ADRs 0006 (Weaviate) and 0007 (FastAPI) added to task list and status.md Key Decisions table. Remaining blockers: shared Pydantic models, Alembic migrations, Dockerfiles, CI pipeline.

---
