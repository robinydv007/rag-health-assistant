# specs/phases/

Each phase has its own directory with four files:

| File | Purpose |
|------|---------|
| `overview.md` | Goal, scope (in/out), success criteria |
| `plan.md` | Group-based execution plan with parallel/sequential ordering |
| `tasks.md` | Granular checkbox task list |
| `history.md` | Append-only log of decisions made during the phase |

## Phase Registry

See `index.json` for machine-readable phase metadata.

| Phase | Name | Status |
|-------|------|--------|
| 0 | Bootstrap | In Progress |
| 1 | Core Services | Planned |
| 2 | Embedding & Indexing | Planned |
| 3 | Admin & LLM Router | Planned |
| 4 | Observability & Hardening | Planned |
| 5 | Production | Planned |

## Rules

- Only one phase is `active` at a time.
- A phase is `complete` only after `/complete-phase` verifies all success criteria.
- `history.md` is append-only — never edit past entries.
- Tasks use `[x]` (done), `[/]` (in-progress), `[ ]` (not started).
