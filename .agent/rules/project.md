# Project Rules

## Navigation (Where to Find Things)

| Question | File |
|----------|------|
| Current state / what phase? | `specs/status.md` |
| What's in the backlog? | `specs/backlog/backlog.md` |
| Phase tasks/progress? | `specs/phases/phase-N-*/tasks.md` |
| Why was X chosen? | `specs/decisions/NNNN-*.md` |
| Roadmap / timeline? | `specs/planning/roadmap.md` |
| Architecture? | `specs/architecture/overview.md` |

> **First file to read: ALWAYS `specs/status.md`.**

---

## Autonomous Behaviors (Always-On Rules)

### Rule 1: Always Orient First
Before ANY work, read `specs/status.md`.

### Rule 2: Auto-Update Tracking After Changes
After completing ANY meaningful work, automatically update:
1. Active phase `tasks.md` — `[x]` complete, `[/]` in-progress
2. `specs/status.md` — if phase progress, blockers, or P0 items changed
3. `specs/changelog/YYYY-MM.md` — log what changed (one line per change)

**Red Flags (STOP and update now):**
- "I'll batch tracking at the end" — context fades; log now
- "Too small to log" — small changes accumulate into invisible drift
- "The diff makes it obvious" — diffs show *what*; logs explain *why*

### Rule 3: Auto-Track Discoveries
When you discover a bug, tech debt, or enhancement:
- Add it to `specs/backlog/backlog.md` immediately
- Mention it to the user

### Rule 4: Pre-Phase Bug Check
Before starting a new phase, scan backlog for P0/P1 bugs.

### Rule 5: Phase Boundary Awareness
When completing the last task: prompt user to run `/complete-phase`.

### Rule 6: Git Lifecycle (Automatic)
- Before ANY code change: check branch; auto-create feature branch if on main/staging
- Auto-commit after each logical unit with conventional commits
- Never auto-merge to staging or main — always ask user

### Rule 7: Plan Before Implementing
For non-trivial work: use `/brainstorm-phase` first.

### Rule 8: Record Phase History
Append to `specs/phases/<active-phase>/history.md` after meaningful changes.

Format (APPEND ONLY):
```
### [TYPE] YYYY-MM-DD — Short title
Topics: topic-1, topic-2
Affects-phases: phase-N-name (or "none")
Affects-specs: path/to/file.md#section (or "none")
Detail: One to three sentences.

---
```

### Rule 9: Doc Sync Protocol
- During a phase: record to history only. Do NOT update other specs.
- At phase completion: run `/sync-docs` BEFORE `/complete-phase`.

### Rule 10: Architecture Specs Stability
Files under `specs/architecture/` are constitutional. READ only during phase; update only at completion.

### Rule 11: Evaluator Discipline
Lock evaluators before optimization loops. Never mutate a locked evaluator — version-bump to v2.

### Rule 12: Verify Before Claim
Run verification before marking `[x]`. Fresh evidence only — not confidence, not "looks right".

---

## Naming Conventions

Backlog IDs: `BUG-NNN` | `FEAT-NNN` | `TD-NNN` | `ENH-NNN`

Priorities: P0 (critical, <1 day) | P1 (high, <1 week) | P2 (medium, <1 phase) | P3 (low)

Branches: `phase-N-name` | `feat/desc` | `fix/desc` | `refactor/desc` | `infra/desc`

Commits: `feat:` | `fix:` | `docs:` | `refactor:` | `chore:` | `infra:`

---

## Project Extensions

> Add project-specific agent rules here.

### Healthcare Rules
- PII/PHI must be scrubbed in Doc Processing before any text goes downstream — always verify this
- Query audit log must be written for every Chat Service request — never skip it
- HIPAA formal audit is Phase 5 — don't claim compliance before then
