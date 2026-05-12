# Data Model

> **Last Updated**: 2026-05-12

---

## PostgreSQL Schema

### documents
Tracks every document uploaded to the system and its processing state.

```sql
CREATE TABLE documents (
    doc_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    job_id          UUID NOT NULL,
    title           TEXT NOT NULL,
    doc_type        TEXT NOT NULL,          -- clinical_guideline | hospital_policy | hl7_standard | drug_formulary | other
    s3_key          TEXT NOT NULL,
    content_type    TEXT NOT NULL,
    uploaded_by     TEXT NOT NULL,          -- user_id
    target_index    TEXT NOT NULL DEFAULT 'live',
    status          TEXT NOT NULL DEFAULT 'pending',
    -- pending | processing | embedding | indexing | indexed | failed
    chunks_total    INTEGER,
    chunks_indexed  INTEGER DEFAULT 0,
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_uploaded_by ON documents(uploaded_by);
```

---

### query_history
Audit log for every question asked through the Chat Service.

```sql
CREATE TABLE query_history (
    query_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         TEXT NOT NULL,
    session_id      TEXT,
    question        TEXT NOT NULL,
    response        TEXT NOT NULL,
    sources         JSONB NOT NULL DEFAULT '[]',
    model_used      TEXT NOT NULL,          -- gpt-4 | claude-3 | llama-2 | mistral-7b
    latency_ms      INTEGER,
    tokens_used     INTEGER,
    index_queried   TEXT NOT NULL DEFAULT 'live',
    pii_detected    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_query_history_user_id ON query_history(user_id);
CREATE INDEX idx_query_history_created_at ON query_history(created_at DESC);
```

---

### indexing_jobs
Tracks re-index operations managed by the Indexing Coordinator.

```sql
CREATE TABLE indexing_jobs (
    job_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shadow_index    TEXT NOT NULL,
    reason          TEXT,
    status          TEXT NOT NULL DEFAULT 'in_progress',
    -- in_progress | ready_to_swap | swapped | failed | rolled_back
    docs_total      INTEGER NOT NULL,
    docs_completed  INTEGER DEFAULT 0,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    swapped_at      TIMESTAMPTZ,
    initiated_by    TEXT NOT NULL
);
```

---

### chunk_audit
Per-chunk write record for compliance. Written by Indexing Service.

```sql
CREATE TABLE chunk_audit (
    audit_id        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id          UUID REFERENCES documents(doc_id),
    chunk_id        TEXT NOT NULL,
    index_name      TEXT NOT NULL,
    embedded_model  TEXT NOT NULL,
    written_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chunk_audit_doc_id ON chunk_audit(doc_id);
```

---

## Vector DB Schema (Weaviate)

### Class: `KnowledgeChunk`

```json
{
  "class": "KnowledgeChunk",
  "description": "A single text chunk from a healthcare document with its embedding",
  "vectorizer": "none",
  "properties": [
    { "name": "docId",       "dataType": ["text"] },
    { "name": "chunkId",     "dataType": ["text"] },
    { "name": "chunkIdx",    "dataType": ["int"] },
    { "name": "text",        "dataType": ["text"] },
    { "name": "docType",     "dataType": ["text"] },
    { "name": "title",       "dataType": ["text"] },
    { "name": "pageNum",     "dataType": ["int"] },
    { "name": "version",     "dataType": ["int"] },
    { "name": "embeddedModel", "dataType": ["text"] },
    { "name": "indexedAt",   "dataType": ["date"] }
  ]
}
```

Index aliases:
- `knowledge-live` → points to active index (e.g., `knowledge-v2`)
- `knowledge-shadow` → points to shadow index during re-index (e.g., `knowledge-v3`)

---

## S3 Structure

```
s3://{bucket}/
  raw-docs/
    {doc_id}/
      {original_filename}          ← raw uploaded file (unchanged)
  
  processed/
    {doc_id}/
      chunks.jsonl                 ← post-scrub, post-parse chunks (debug only)
  
  models/
    biogpt/                        ← model weights (if self-hosted)
    scibert/
    llama-2/
    mistral-7b/
```

Lifecycle policy: `raw-docs/` → Glacier after 90 days, delete after 7 years (HIPAA retention).
