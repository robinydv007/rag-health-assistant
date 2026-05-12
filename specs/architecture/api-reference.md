# API Reference

> **Version**: v1  
> **Base URL**: `https://api.{org}.internal/api/v1`  
> **Auth**: JWT Bearer token (validated by AWS API Gateway Lambda Authorizer)

---

## Endpoints

### Chat Service

#### POST /knowledge/ask
Ask a question — returns a streamed answer with source citations.

**Request**
```json
{
  "question": "What is the recommended insulin dosing for Type 2 diabetes per our formulary?",
  "user_id": "usr_abc123",
  "session_id": "sess_xyz789"
}
```

**Response** — Server-Sent Events (SSE) stream
```
data: {"token": "The recommended", "done": false}
data: {"token": " starting dose", "done": false}
...
data: {"token": ".", "done": true, "sources": [
  {"doc_id": "doc_001", "title": "Formulary 2025", "page": 42, "chunk": "...relevant excerpt..."}
]}
```

**Error codes**: 400 (invalid question), 401 (missing/invalid JWT), 429 (rate limit), 503 (LLM unavailable)

---

#### GET /knowledge/history
Retrieve past queries for a user or check document upload status.

**Query params**: `user_id`, `limit` (default 20), `offset`, `doc_id` (filter by upload job)

**Response**
```json
{
  "queries": [
    {
      "query_id": "q_001",
      "question": "...",
      "asked_at": "2026-05-12T10:30:00Z",
      "sources_count": 3
    }
  ],
  "total": 45
}
```

---

### Uploader Service

#### POST /knowledge/ingest
Upload a document to the knowledge base.

**Request** — `multipart/form-data`
- `file`: binary (PDF, DOCX, TXT, HL7)
- `title`: string
- `doc_type`: `clinical_guideline | hospital_policy | hl7_standard | drug_formulary | other`
- `target_index`: `live` (default) | `shadow` (for re-index flows)

**Response** — HTTP 202
```json
{
  "job_id": "job_abc123",
  "doc_id": "doc_xyz789",
  "status": "pending",
  "status_url": "/api/v1/knowledge/history?doc_id=doc_xyz789"
}
```

---

### Admin Service

#### GET /health
Aggregate health check across all services and infrastructure.

**Response**
```json
{
  "status": "healthy",
  "services": {
    "chat": "healthy",
    "uploader": "healthy",
    "doc_processing": "healthy",
    "embedding": "healthy",
    "indexing": "healthy"
  },
  "queues": {
    "sqs_1": {"depth": 0, "dlq_depth": 0},
    "sqs_2": {"depth": 12, "dlq_depth": 0},
    "sqs_3": {"depth": 3, "dlq_depth": 0}
  },
  "vector_db": "healthy",
  "postgres": "healthy"
}
```

---

#### POST /admin/reindex
Trigger a full re-index of the knowledge base (zero downtime).

**Request**
```json
{ "reason": "Quarterly policy update batch" }
```

**Response** — HTTP 202
```json
{
  "job_id": "reindex_job_001",
  "shadow_index": "knowledge-v3",
  "docs_queued": 847,
  "status": "in_progress"
}
```

---

#### GET /admin/dlq
Inspect failed messages across all dead letter queues.

**Response**
```json
{
  "dlq_1": {"count": 0, "messages": []},
  "dlq_2": {"count": 2, "messages": [{"message_id": "...", "error": "...", "retries": 3}]},
  "dlq_3": {"count": 0, "messages": []}
}
```

---

#### POST /admin/dlq/requeue
Move messages from a DLQ back to its main queue for retry.

**Request**
```json
{
  "queue": "dlq_2",
  "message_ids": ["msg_001", "msg_002"]
}
```

**Response** — HTTP 200
```json
{ "requeued": 2, "failed": 0 }
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/knowledge/ask` | 60 req/min per user |
| `/knowledge/ingest` | 10 req/min per user |
| `/knowledge/history` | 120 req/min per user |
| `/admin/*` | 30 req/min (ops only) |

---

## SQS Message Schemas

### SQS 1 — Doc Processing Job
```json
{
  "doc_id": "doc_xyz789",
  "s3_key": "raw-docs/doc_xyz789/formulary-2025.pdf",
  "content_type": "application/pdf",
  "uploaded_by": "usr_abc123",
  "target_index": "live",
  "job_id": "job_abc123",
  "uploaded_at": "2026-05-12T10:30:00Z"
}
```

### SQS 2 — Chunk Embedding Job
```json
{
  "doc_id": "doc_xyz789",
  "chunks": [
    {
      "chunk_id": "doc_xyz789_chunk_001",
      "text": "...scrubbed chunk text...",
      "metadata": {
        "doc_type": "drug_formulary",
        "page_num": 42,
        "chunk_idx": 0,
        "version": 1,
        "target_index": "live"
      }
    }
  ]
}
```

### SQS 3 — Indexing Job
```json
{
  "doc_id": "doc_xyz789",
  "chunk_id": "doc_xyz789_chunk_001",
  "embedding": [0.123, -0.456, ...],
  "metadata": { "...": "same as SQS 2 metadata" },
  "target_index": "live"
}
```
