# Phase 1 History

> Append-only decision log. Format: `### [TYPE] YYYY-MM-DD — Title`

---

### [NOTE] 2026-05-12 — Phase 1 brainstormed; scope locked

Topics: phase-planning, scope, brainstorm
Affects-phases: phase-1-core-services
Affects-specs: specs/planning/roadmap.md, specs/phases/phase-1-core-services/overview.md
Detail: Phase 1 brainstormed via /brainstorm-phase while Phase 0 Groups 4–5 were still in progress (pre-planning). Scope locked to Chat, Uploader, and Doc Processing services. Five key decisions made (direct LLM calls, MinIO, defer HL7, static synonym dict, Presidio). Phase files written and committed.

---

### [DECISION] 2026-05-12 — MinIO chosen as S3 local dev replacement

Topics: local-dev, s3, minio
Affects-phases: phase-1-core-services
Affects-specs: none
Detail: MinIO chosen over LocalStack as the S3-compatible local container. Simpler and lighter for a project that only uses S3 (not other AWS services locally). boto3 S3 client pointed at http://minio:9000 in local dev via S3_ENDPOINT_URL env var; empty in staging/prod uses real AWS S3.

---

### [DECISION] 2026-05-12 — Direct LLM calls in Phase 1; full router deferred to Phase 3

Topics: llm, chat-service, llm-router
Affects-phases: phase-1-core-services, phase-3-admin-llm-router
Affects-specs: specs/architecture/services.md#llm-router
Detail: Phase 1 uses a direct shared LLM client (OpenAI or Anthropic, chosen via LLM_PROVIDER env var) rather than the full LLM Router. The LLM Router with circuit breaker and Llama 2 fallback is Phase 3 scope. Tests use LLM_MOCK=true to return fixture responses without real API calls.

---

### [DECISION] 2026-05-12 — Placeholder zero-vectors for Chat Service search in Phase 1

Topics: chat-service, weaviate, embeddings, search-quality
Affects-phases: phase-1-core-services, phase-2-embedding-indexing
Affects-specs: specs/architecture/services.md#chat-service
Detail: Since real BioGPT/SciBERT embeddings are Phase 2 scope, the Chat Service uses 768-dim zero-vectors for the nearVector component of Weaviate hybrid search. BM25 keyword search still works. Search quality is intentionally low in Phase 1 — the goal is to validate pipeline structure, not search quality.

---

### [DECISION] 2026-05-12 — Microsoft Presidio chosen for PII scrubbing

Topics: doc-processing, pii, presidio, hipaa
Affects-phases: phase-1-core-services
Affects-specs: specs/architecture/services.md#doc-processing-service
Detail: Presidio chosen over AWS Comprehend Medical for Phase 1 because it runs fully locally in docker-compose with no AWS credentials needed. Covers all required entities (PERSON, DATE_TIME, US_SSN, PHONE_NUMBER, EMAIL_ADDRESS, LOCATION, MEDICAL_LICENSE, NPI). AWS Comprehend Medical may be evaluated in Phase 5 HIPAA audit if Presidio recall proves insufficient for clinical entity types.

---

### [DECISION] 2026-05-12 — HL7/EHR parsing deferred to Phase 2

Topics: doc-processing, hl7, parsing, scope
Affects-phases: phase-1-core-services, phase-2-embedding-indexing
Affects-specs: specs/architecture/services.md#doc-processing-service
Detail: Phase 1 supports PDF, DOCX, and TXT only. HL7/EHR parsing (v2, FHIR, CDA) requires a custom parser and is significant additional scope. Deferred to Phase 2 alongside the embedding pipeline. The parser dispatch table is extensible by design — adding HL7 requires a new parser module without modifying the consumer loop.

---

### [DECISION] 2026-05-12 — Static synonym dictionary for query expansion

Topics: chat-service, query-expansion, search-quality
Affects-phases: phase-1-core-services
Affects-specs: specs/architecture/services.md#chat-service
Detail: A YAML lookup of ~100–200 medical abbreviations and synonyms chosen over LLM-based expansion. Zero latency, no API cost, deterministic behavior. LLM-based expansion can be added later as part of ENH-002 if static dict proves insufficient after Phase 2 search quality evaluation (FEAT-025).

---
