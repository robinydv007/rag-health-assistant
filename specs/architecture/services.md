# Service Specifications

> **Last Updated**: 2026-05-12

---

## Chat Service

**Path**: `services/chat-service/`  
**Language**: Python / FastAPI  
**Trigger**: HTTP POST `/api/v1/knowledge/ask` (user-facing, via API Gateway)  
**Scaling**: Active connection count

### Responsibilities
1. Expand user query with medical synonyms and abbreviation expansions
2. Hybrid search: semantic (vector) + keyword (BM25) against Vector DB
3. Rerank results by relevance (cross-encoder or Cohere Rerank)
4. Build prompt with top-K results + few-shot examples
5. Call LLM Router (streaming), strip PII from response
6. Add source citations to response
7. Write query + response to PostgreSQL audit log
8. Stream response to user via SSE (Server-Sent Events)

### Key Interfaces
- **Input**: `POST /api/v1/knowledge/ask` — `{ question: str, user_id: str }`
- **Output**: SSE stream — `{ token: str, sources: List[Source], done: bool }`
- **GET** `/api/v1/knowledge/history` — paginated query history for a user

---

## Uploader Service

**Path**: `services/uploader-service/`  
**Language**: Python / FastAPI  
**Trigger**: HTTP POST `/api/v1/knowledge/ingest` (user-facing, via API Gateway)  
**Scaling**: Request rate

### Responsibilities
1. Accept multipart file upload (PDF, DOCX, TXT, EHR)
2. Write raw file to S3 under `raw-docs/{doc_id}/`
3. Insert document record into PostgreSQL with `status=pending`
4. Push SQS 1 message: `{ doc_id, s3_key, content_type, uploaded_by, target_index }`
5. Return HTTP 202 with `{ job_id, status_url }`

### Key Interfaces
- **Input**: `POST /api/v1/knowledge/ingest` — multipart form, `file` + metadata
- **Output**: `{ job_id: str, status_url: str }` (HTTP 202)
- Does NOT parse or read file content — keeps the service fast

---

## Doc Processing Service

**Path**: `services/doc-processing/`  
**Language**: Python  
**Trigger**: SQS 1 consumer  
**Scaling**: SQS 1 queue depth

### Responsibilities
1. Consume message from SQS 1
2. Download file from S3
3. **PII/PHI scrubbing** — detect and mask before any text is forwarded
4. Parse file format (PDF → PyPDF2/pdfplumber; DOCX → python-docx; TXT; EHR/HL7 → custom parser)
5. Split into overlapping chunks (512 tokens, 50-token overlap)
6. Tag each chunk with metadata: `{ doc_id, chunk_idx, version, target_index, page_num }`
7. Push chunk batch to SQS 2
8. Update PostgreSQL `documents.status = processing`

### PII Scrubbing
- Tool: AWS Comprehend Medical or Microsoft Presidio
- Entities detected: Name, DOB, SSN, MRN, Address, Phone, Date, NPI
- Replacement: `[REDACTED-{entity_type}]` tokens
- Scrubbing happens BEFORE any text reaches SQS 2 — downstream services never see raw PHI

---

## Embedding Service

**Path**: `services/embedding-service/`  
**Language**: Python  
**Trigger**: SQS 2 consumer  
**Compute**: EC2 GPU instance (g4dn.xlarge or similar)  
**Scaling**: SQS 2 queue depth

### Responsibilities
1. Consume chunk batches from SQS 2
2. Batch 64 chunks together for GPU efficiency
3. Generate embeddings using BioGPT or SciBERT (medical domain models)
4. Push `{ chunk_id, embedding_vector, metadata }` to SQS 3

### Model Strategy
- Primary: **BioGPT** (Microsoft) — generative medical model, strong on clinical text
- Secondary: **SciBERT** (AllenAI) — bidirectional, strong on scientific text
- Model is configurable via env var — switching models does not affect other services

---

## Indexing Service

**Path**: `services/indexing-service/`  
**Language**: Python  
**Trigger**: SQS 3 consumer  
**Scaling**: SQS 3 queue depth

### Responsibilities
1. Consume vector batches from SQS 3
2. Write vectors to Vector DB (live index or shadow index based on `target_index` flag)
3. Update PostgreSQL `documents.chunks_indexed` counter
4. Write per-chunk audit entry
5. Notify Indexing Coordinator (via SQS or internal API) that chunk is done

### Indexing Coordinator (sub-component)
- Tracks chunk completion per document
- When all chunks for all documents in a re-index are done → signals Admin Service
- State stored in PostgreSQL `indexing_jobs` table

---

## Admin Service

**Path**: `services/admin-service/`  
**Language**: Python / FastAPI  
**Trigger**: Internal HTTP (ops tooling only — NOT routed through API Gateway for user traffic)  
**Scaling**: Fixed at 2 replicas (minimal load)

### Responsibilities
1. `POST /admin/reindex` — Create shadow index, push all S3 paths to SQS 1 with shadow flag
2. `POST /admin/swap-index` — Swap `index-live` alias to new index (after coordinator signals ready)
3. `GET /admin/dlq` — Inspect failed messages in all 3 DLQs
4. `POST /admin/dlq/requeue` — Move messages from DLQ back to main queue
5. `GET /api/v1/health` — Aggregate health check across all services

### Elevated Permissions
- Can write to Vector DB index aliases
- Can read/write all 3 SQS DLQs
- Has RDS write access to `indexing_jobs` and `documents` tables
- Deliberately NOT reachable by user-facing API routes

---

## LLM Router (shared component)

**Path**: `shared/llm_router/`  
**Used by**: Chat Service

### Logic
```
request → check circuit breaker state
  CLOSED → try GPT-4 / Claude 3
    success → return
    failure (3 tries or >5s) → OPEN circuit
  OPEN → route to Llama 2 / Mistral (self-hosted)
  HALF_OPEN → probe primary; if success → CLOSE circuit
```

### Models
| Tier | Provider | Model |
|------|----------|-------|
| Primary | OpenAI / Anthropic | GPT-4 / Claude 3 |
| Fallback | Self-hosted | Llama 2 13B / Mistral 7B |
