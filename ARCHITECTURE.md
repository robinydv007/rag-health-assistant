# RAG Healthcare Knowledge Assistant — Architecture Design

**Version:** 1.0  
**Role:** Technical Lead Backend

---

## 1. Summary

This system is an internal AI assistant for healthcare teams. Users can ask medical questions and get answers from uploaded documents like clinical guidelines, hospital policies, and HL7 standards. The system supports 500+ users at the same time, responds in under 2 seconds, and follows HIPAA rules.

The system is built using microservices — 6 services in total, with a 3-step async pipeline for document processing, and a way to update the knowledge base without any downtime.

---

## 2. Architecture Diagram

```
                        [ Users ]
                            |
                    [ AWS API Gateway ]
                  JWT · Rate Limit · Route
                /           |             \
               /            |              \
    [ Chat Service ]  [ Uploader Service ]  [ Admin Service ]
    query expand       file → S3              reindex
    hybrid search      DB entry               alias swap
    rerank + LLM       push SQS 1             DLQ mgmt
    stream response         |
         |             [ SQS 1 ] ←— DLQ 1
         |                  |
         |        [ Doc Processing ]
         |        PII scrub · chunk
         |        tag metadata
         |                  |
         |             [ SQS 2 ] ←— DLQ 2
         |                  |
         |        [ Embedding Service ]
         |        BioGPT / SciBERT (GPU)
         |        EC2 GPU instance
         |                  |
         |             [ SQS 3 ] ←— DLQ 3
         |                  |
         |        [ Indexing Service ]        [ Indexing Coordinator ]
         |        write vectors                track chunk completion
         |        update PG status   ————————> signal admin when done
         |
    ─────────────────────────────────────
    [ Vector DB ]  [ PostgreSQL ]  [ S3 ]
    embeddings     audit logs       raw docs
    HA replica     query history    lifecycle
    ─────────────────────────────────────
              [ LLM Router ]
         GPT-4/Claude → Llama fallback

    ─────────────────────────────────────
              [ Observability ]
     Prometheus · Grafana · Jaeger · ELK
    ─────────────────────────────────────
```

---

## 3. Core Design Decisions

**One job per service.** Each service does only one thing. No service handles two different pipeline steps.

**No service waits for another.** Every service finishes its job, pushes to a queue, and moves to the next task right away. This means no wasted time waiting and each service can scale on its own.

**Queues control scaling.** Each SQS queue shows us how much work is pending. We use that queue size to decide when to add more pods — not CPU usage.

**Admin is separate.** The admin service handles things like re-indexing and fixing failed jobs. Normal user-facing services never get those permissions.

**No downtime on updates.** When we update the knowledge base, we build a new index in the background. We only switch to it when it's fully ready. Users never see any interruption.

---

## 3. Services

### API Gateway
We use **AWS API Gateway**. It is fully managed by AWS — no infra to run or maintain. It handles JWT validation (via a Lambda authorizer), rate limiting (built-in throttling per route), and routes requests to the right ECS service. We do not have a separate auth service because JWT checks are simple operations — adding a separate service just for that would slow down every request for no real benefit.

---

### Chat Service _(handles user queries)_
This service takes user questions and returns answers.

Steps: expand the query (add medical synonyms, full forms of abbreviations) → search Vector DB using both semantic search and keyword search → rerank results by relevance → build a prompt with the top results and some examples → call LLM and stream the response back to user → remove any PII from response → add source citations → save query to audit log.

We use SSE (server-sent events) to stream the response so users see the first words quickly, even if the full answer takes a bit longer.

---

### Uploader Service _(start of document pipeline)_
Does only 3 things: save the file to S3, create a row in PostgreSQL with doc ID and status, push a message to SQS 1 with the file location. Then returns a job ID to the client right away (HTTP 202). It never reads or parses the file — that keeps it fast and simple.

---

### Doc Processing Service _(pipeline step 1)_
Picks up messages from SQS 1. Reads the file from S3 → finds and removes any PII/PHI from the text (this must happen here, before text goes anywhere else) → parses the file format (PDF, DOCX, TXT, EHR) → splits text into overlapping chunks so context is not lost at boundaries → adds metadata like doc ID, chunk number, version, and target index → pushes chunks to SQS 2. Then immediately picks up the next message from SQS 1.

PII removal happens here because this is the first place we actually read the file content. After this step, no downstream service ever sees unmasked patient data.

---

### Embedding Service _(pipeline step 2)_
Picks up chunk batches from SQS 2. Converts text chunks into vectors using BioGPT or SciBERT (medical-specific models). Processes 64 chunks at a time on GPU to keep it efficient. Pushes results to SQS 3. This service does not know anything about the database or which index to write to — it just converts text to vectors and passes them on. This makes it easy to swap the model later without touching other services.

---

### Indexing Service _(pipeline step 3)_
Picks up vector results from SQS 3. Writes vectors to Vector DB (to live index or shadow index based on a flag in the message) → updates doc status in PostgreSQL → writes audit log → tells the indexing coordinator that chunks are done. Small and cheap to run, focused only on DB writes.

---

### Admin Service _(internal operations only)_
Handles background system tasks — no user traffic goes here. Used to trigger re-indexing, swap indexes, check failed jobs in the dead letter queues, and get system health. It has higher permissions than other services (can write to index aliases, access all queues) so it is kept separate on purpose.

---

### LLM Router + Circuit Breaker
Decides which LLM to use. Normally uses GPT-4 or Claude 3. If those are slow or failing, it automatically switches to a self-hosted Llama 2 or Mistral model. This means if the main LLM provider has an outage, users still get answers — just from the fallback model. This is important to meet the 99.9% uptime goal.

---

## 4. Async Pipeline

```
Uploader → SQS 1 → Doc Processing → SQS 2 → Embedding → SQS 3 → Indexing Service
```

Each queue has a dead letter queue (DLQ). If a message fails 3 times, it moves to the DLQ and an alert fires. The timeout on each queue is set long enough so that if a pod crashes mid-job, the message becomes available again for another pod to pick up — no work is lost.

**Indexing Coordinator** tracks how many chunks have been written for each document. When all chunks for all documents are done, it tells the admin service the new index is ready to go live.

---

## 5. Re-Index Flow (Zero Downtime)

1. Operator calls `POST /admin/reindex`. Admin creates a new shadow index `v2` and marks all docs as pending.
2. Admin pushes all existing document paths from S3 to SQS 1, with a flag saying "write to shadow index v2".
3. The normal ingestion pipeline runs. Indexing service writes everything to `v2`. The current live index `v1` is not touched at all.
4. Indexing coordinator sees all chunks are done and tells admin.
5. Admin swaps the index alias — `index-live` now points to `v2`. Chat service always reads from `index-live` so it switches automatically, with no restart and no downtime.
6. Old index `v1` is kept for 24 hours in case we need to roll back. After that it gets deleted.

---

## 6. API Reference

| Method | Endpoint | Owner | Description |
|--------|----------|-------|-------------|
| POST | `/api/v1/knowledge/ask` | Chat service | Ask a question, get streamed answer with sources |
| POST | `/api/v1/knowledge/ingest` | Uploader | Upload a document, get back job ID |
| GET | `/api/v1/knowledge/history` | Chat service | See past queries or check upload status |
| GET | `/api/v1/health` | Admin | Check if all services are healthy |
| POST | `/api/v1/admin/reindex` | Admin | Start a full re-index of knowledge base |
| GET | `/api/v1/admin/dlq` | Admin | See failed jobs |
| POST | `/api/v1/admin/dlq/requeue` | Admin | Retry failed jobs |

---

## 7. Scaling

| Service | What slows it down | When we add more tasks |
|---------|-------------------|----------------------|
| Chat service | Too many users asking questions | High active connections |
| Uploader | Lots of file uploads | High request rate |
| Doc processing | CPU work — PII scanning, chunking | SQS 1 queue getting long |
| Embedding | GPU processing | SQS 2 queue getting long |
| Indexing service | Writing to DB | SQS 3 queue getting long |
| Admin | Almost no load | Fixed at 2 tasks |

---

## 8. Tech Stack

| Component | What we use | Why |
|-----------|------------|-----|
| API Gateway | AWS API Gateway | Managed, JWT auth via Lambda authorizer, built-in throttling, no infra to run |
| Backend | Python FastAPI | Good for async, streaming, and ML work |
| RAG framework | LangChain | Handles retrieval, prompts, and chaining well |
| LLM primary | GPT-4 / Claude 3 | Best quality for medical questions |
| LLM fallback | Llama 2 / Mistral 7B | Self-hosted, works even if main provider is down |
| Embedding model | BioGPT / SciBERT | Trained on medical text, better results |
| Vector DB | Weaviate or pgvector | Supports both semantic and keyword search |
| SQL DB | PostgreSQL | Reliable, good for audit logs |
| Queue | AWS SQS | Managed service, has DLQ built in |
| File storage | S3 | Cheap, has versioning and lifecycle rules |
| Orchestration | AWS ECS (Fargate) | Fully managed, no cluster to operate, auto-scaling via CloudWatch, simpler than EKS |
| CI/CD | GitHub Actions | Runs tests, builds, and deploys automatically |
| Monitoring | Prometheus + Grafana, Jaeger, ELK | Metrics, tracing, and logs |

---

## 9. Performance Targets

| What | Goal | How |
|------|------|-----|
| Response time (p95) | Under 2 seconds | Streaming, caching, limit reranker results |
| Concurrent users | 500+ | Scale pods horizontally |
| Documents processed | 1000+ per minute | Scale GPU workers based on queue size |
| Uptime | 99.9% | HA databases, LLM fallback, multi-zone setup |
| Re-index downtime | Zero | Shadow index + alias swap |

---

## 10. What Happens When Things Break

| Problem | What we do |
|---------|-----------|
| Main LLM is down | Circuit breaker switches to self-hosted fallback |
| Vector DB primary crashes | Replica takes over automatically |
| PostgreSQL primary crashes | Standby takes over automatically |
| Any pipeline service crashes | SQS retries the message, goes to DLQ after 3 fails |
| New index has bad quality | Swap alias back to old index (kept for 24 hrs) |
| DLQ keeps growing | Alert fires, operator checks and retries via admin API |
