# Phase 2 History

> Append-only decision log. Format: `### [TYPE] YYYY-MM-DD — Title`

---

### [NOTE] 2026-05-13 — Phase 2 brainstormed; scope locked

Topics: phase-planning, scope, brainstorm
Affects-phases: phase-2-embedding-indexing
Affects-specs: specs/planning/roadmap.md, specs/phases/phase-2-embedding-indexing/overview.md
Detail: Phase 2 brainstormed via /brainstorm-phase while Phase 1 Group 4 (Docker wiring) is pending environment access. Scope locked to Embedding Service, Indexing Service + Coordinator, DLQ monitor, Chat Service query embedding update. Six key decisions made (see entries below). Phase files written and committed.

---

### [DECISION] 2026-05-13 — HL7/EHR parsing deferred again to Phase 3

Topics: doc-processing, hl7, parsing, scope
Affects-phases: phase-2-embedding-indexing, phase-3-admin-llm-router
Affects-specs: specs/architecture/services.md#doc-processing-service
Detail: HL7 was already deferred from Phase 1 to Phase 2. It is deferred again to Phase 3. Phase 2 is tightly scoped to the embedding pipeline. The parser dispatch table remains extensible — adding HL7 support requires only a new parser module.

---

### [DECISION] 2026-05-13 — BiomedBERT via HuggingFace Serverless Inference API chosen over self-hosted GPU

Topics: embedding, biomedbert, huggingface, gpu, architecture
Affects-phases: phase-2-embedding-indexing
Affects-specs: specs/architecture/services.md#embedding-service, specs/decisions/0003-medical-embedding-models.md
Detail: Original plan (ADR 0003) was self-hosted BioGPT/SciBERT on EC2 GPU. Replaced by `microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext` called via the HuggingFace Serverless Inference API. BiomedBERT is trained on 14M PubMed abstracts and full texts — medical domain coverage is equivalent or better. Removes EC2 GPU instance entirely, simplifying infrastructure. Rate limits on the free/serverless tier are acceptable for Phase 2 development volume. ADR 0003 amendment (`0003a-biomedbert-hf-inference-api.md`) to be written in Group 0.

---

### [DECISION] 2026-05-13 — Provider abstraction: EMBEDDING_PROVIDER env var for future GPU switch

Topics: embedding, architecture, extensibility
Affects-phases: phase-2-embedding-indexing
Affects-specs: none
Detail: The shared `EmbeddingClient` abstraction (`shared/clients/embedding_client.py`) exposes `HFInferenceClient` and `HTTPEndpointClient` behind a factory. `EMBEDDING_PROVIDER=hf_inference` uses the HF Serverless API (Phase 2 default). `EMBEDDING_PROVIDER=http_endpoint` routes to any HTTP model server — self-hosted GPU (Triton, vLLM, custom FastAPI over transformers) — using the same `{"inputs": [...]}` → `[[vector], ...]` contract. Switching to self-hosted GPU later requires only an env var change and no code changes.

---

### [DECISION] 2026-05-13 — DLQ alerting implemented as logic + webhook hook; CloudWatch deferred to Phase 5

Topics: dlq, alerting, observability, cloudwatch
Affects-phases: phase-2-embedding-indexing, phase-5-production
Affects-specs: specs/planning/roadmap.md#phase-2
Detail: `shared/utils/dlq_monitor.py` checks DLQ depths every 60 seconds and dispatches alerts (log WARNING + optional HTTP webhook via `DLQ_ALERT_WEBHOOK_URL`). Real CloudWatch metrics and SNS alarms are deferred to Phase 5 when production AWS infrastructure is provisioned. The webhook hook is sufficient for Phase 2 developer visibility.

---

### [DECISION] 2026-05-13 — Search relevance evaluation set (FEAT-025) deferred to Phase 3

Topics: quality, evaluation, search, feat-025
Affects-phases: phase-2-embedding-indexing, phase-3-admin-llm-router
Affects-specs: specs/backlog/backlog.md
Detail: FEAT-025 (fixed corpus of query→chunk gold pairs + Recall@5/MRR benchmark script) is deferred to Phase 3. Phase 2 validates the pipeline is wired correctly and embeddings are non-zero. Phase 3 needs the eval set for LLM router tuning; building it there avoids a half-baked set being locked in Phase 2 before the full system is visible.

---

### [DECISION] 2026-05-13 — Indexing Coordinator is a sub-component of Indexing Service, not a separate service

Topics: indexing, coordinator, architecture
Affects-phases: phase-2-embedding-indexing
Affects-specs: specs/architecture/services.md#indexing-service
Detail: The architecture spec describes the Indexing Coordinator as a sub-component. Phase 2 implements it as `services/indexing-service/src/coordinator.py` — called inline after each successful PG increment. It sets `documents.status = indexed` when `chunks_indexed == chunks_total`. The `indexing_jobs` table (used by the Admin Service re-index flow) is created via migration in Group 0 but remains unused until Phase 3.

---

### [ARCH_CHANGE] 2026-05-13 — ADR 0003 amendment needed: self-hosted GPU replaced by HF Inference API

Topics: embedding, adr, architecture
Affects-phases: phase-2-embedding-indexing
Affects-specs: specs/decisions/0003-medical-embedding-models.md, specs/architecture/services.md#embedding-service
Detail: ADR 0003 specified BioGPT/SciBERT on EC2 GPU. Phase 2 replaces this with BiomedBERT via HF Serverless API, removing the EC2 GPU requirement. Amendment `specs/decisions/0003a-biomedbert-hf-inference-api.md` to be written in Group 0 as a Group 0 deliverable. The S3 `models/biogpt/` and `models/scibert/` paths in the data model are now unused — note in amendment.

---
