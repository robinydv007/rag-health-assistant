# specs/

Specification-driven project documentation. The authoritative source of truth for what this project is, where it is, and why decisions were made.

## Structure

```
specs/
  vision/
    project-charter.md      ← problem, solution, stakeholders, scope
    principles.md           ← engineering principles that resolve trade-offs
    success-criteria.md     ← measurable completion criteria per phase
  
  architecture/             ← constitutional docs (monorepo only)
    overview.md             ← system architecture, service map, data stores
    services.md             ← detailed spec for each service
    api-reference.md        ← HTTP endpoints + SQS message schemas
    data-model.md           ← PostgreSQL, Weaviate, S3 schemas
    adrs/                   ← architecture-level ADRs
  
  planning/
    roadmap.md              ← release plan and phase summaries
  
  phases/
    index.json              ← machine-readable phase registry
    phase-0-bootstrap/
      overview.md           ← phase goal, scope, success criteria
      plan.md               ← group-based execution plan
      tasks.md              ← granular checklist
      history.md            ← append-only decision log
  
  decisions/
    README.md               ← ADR index
    0000-template.md        ← ADR template
    NNNN-title.md           ← one ADR per significant decision
    impact-map.json         ← topics → affected spec files (for /sync-docs)
  
  backlog/
    backlog.md              ← bugs, features, tech debt, enhancements
    details/                ← detailed specs for complex backlog items
  
  benchmarks/               ← locked evaluation sets (AI/ML quality gates)
  
  changelog/
    YYYY-MM.md              ← monthly change log
  
  status.md                 ← ALWAYS READ FIRST — current phase, blockers, P0 items
```

## Rules

- **`specs/status.md`** is always the first file to read — it orients you to the current state.
- **`specs/architecture/`** files are constitutional — read-only during phase work; update only at phase completion via `/sync-docs`.
- **`specs/phases/*/history.md`** is append-only — log decisions as they happen, not at the end.
- **`specs/decisions/`** stores ADRs — one file per significant decision, written before the decision is implemented.
