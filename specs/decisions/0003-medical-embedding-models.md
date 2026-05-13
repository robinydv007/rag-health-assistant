# ADR 0003 — BioGPT/SciBERT for Domain-Specific Medical Embeddings

> **Status**: superseded
> **Date**: 2026-05-12
> **Supersedes**: N/A
> **Superseded-By**: [ADR 0003a — OpenAI text-embedding-3-large (via BiomedBERT amendment)](0003a-biomedbert-hf-inference-api.md)

## Context

The RAG system's retrieval quality depends heavily on the embedding model used. When a clinician asks "What is the recommended dose of metformin for Type 2 diabetes?", the embedding model must understand that "metformin", "T2DM", "dosing protocol", and "glycemic control" are semantically related concepts — not just token similarities.

General-purpose embedding models (OpenAI `text-embedding-ada-002`, Sentence-BERT) are trained on general web text. Medical literature has a distinct vocabulary: drug names, disease codes (ICD-10), clinical abbreviations, and specialized terminology that general models handle poorly.

The specific problem: general models may score a clinical guideline about "insulin resistance" as less similar to a question about "diabetes management" than a general-purpose article. This reduces retrieval precision in exactly the domain where accuracy matters most.

The system also handles HL7 standards and EHR exports — structured clinical data formats that general models have no training signal for.

## Decision

Use **BioGPT** (Microsoft, primary) and **SciBERT** (AllenAI, secondary) as the embedding models, deployed on EC2 GPU instances. The model is selected via environment variable — switching does not require code changes in other services.

- **BioGPT**: Generative model pre-trained on PubMed literature. Strong on clinical reasoning, drug interactions, and treatment guidelines.
- **SciBERT**: Bidirectional transformer pre-trained on scientific literature (biomedical focus). Strong on dense structured text like drug formularies and HL7 schemas.

Both models produce embeddings optimized for medical semantic similarity — the core metric this system depends on.

## Consequences

### Positive
- Substantially higher retrieval precision on medical queries compared to general models
- Both models are open-source and self-hosted — no per-call API cost; predictable GPU cost
- Model swap is configuration-only — Embedding Service is model-agnostic

### Negative
- Requires GPU instances (EC2 g4dn.xlarge or similar) — higher infrastructure cost than CPU-only embedding
- Self-hosted model management: version pinning, model download, weights storage in S3
- Inference throughput lower than OpenAI's hosted endpoints (mitigated by batching 64 chunks/GPU call)

### Risks
- Model drift: if clinical guidelines use terminology that was not in the training corpus (new drug names, updated ICD codes), retrieval quality may degrade. Mitigated by the evaluation set in `specs/benchmarks/` and planned quarterly re-evaluation.
- GPU instance availability: EC2 GPU spot instances can be interrupted. Mitigation: on-demand instance for production; spot for batch backlog.

## Alternatives Considered

| Option | Why Rejected |
|--------|-------------|
| OpenAI `text-embedding-ada-002` | General-purpose; poor medical vocabulary; per-call cost at scale; external dependency |
| Sentence-BERT (general) | Trained on NLI/STSb — good for general similarity, poor for clinical specificity |
| BioBERT | Older; BioGPT outperforms on most clinical benchmarks; SciBERT covers the gap |
| Fine-tuning a general model | Expensive to produce training data; BioGPT/SciBERT provide this out of the box |
