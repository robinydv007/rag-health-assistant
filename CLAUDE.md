# Project Rules: RAG Healthcare Knowledge Assistant

> Claude Code configuration for this project.
> Agent rules live in `.agent/rules/project.md`.

## Navigation (Where to Find Things)

| Question | File |
|----------|------|
| Current state / what phase? | `specs/status.md` |
| What's in the backlog? | `specs/backlog/backlog.md` |
| Phase tasks/progress? | `specs/phases/phase-N-*/tasks.md` |
| Why was X chosen? | `specs/decisions/NNNN-*.md` |
| Roadmap / timeline? | `specs/planning/roadmap.md` |
| Architecture overview? | `specs/architecture/overview.md` |
| Service specs? | `specs/architecture/services.md` |
| API reference? | `specs/architecture/api-reference.md` |
| Data model? | `specs/architecture/data-model.md` |
| How to contribute? | `docs/developer-guide.md` |

> **First file to read: ALWAYS `specs/status.md`.**

---

## Autonomous Behaviors (Always-On Rules)

### Rule 1: Always Orient First

Before ANY work, read `specs/status.md`. This tells you:
- What phase is active
- What's blocking progress
- What P0 items need attention

### Rule 2: Auto-Update Tracking After Changes

After completing ANY meaningful work, automatically update:

1. **Active phase `tasks.md`** — mark completed `[x]`, in-progress `[/]`
2. **`specs/status.md`** — if phase progress, blockers, or P0 items changed
3. **`specs/changelog/YYYY-MM.md`** — log what changed (one line per change)

Use the built-in **TodoWrite** tool to track in-session task progress. Do NOT wait for the user to ask you to update tracking.

#### Why
Tracking debt compounds invisibly. A task list one day stale is recoverable; one week stale is fiction. Status drift is how phases silently lose direction.

#### Red Flags — STOP and update tracking now

| If you find yourself thinking… | …STOP and update before doing anything else |
|---|---|
| "I'll batch the tracking updates at the end" | The end never comes — context fades and details get lost |
| "This change is too small to log" | Small changes accumulate into invisible drift |
| "The diff makes it obvious what changed" | The diff shows *what*; the changelog explains *why* |
| "The user can read git log" | Git log doesn't index by phase or backlog ID |
| "I'll log this as part of the next bigger update" | Bigger updates conflate decisions and lose per-step reasoning |

### Rule 3: Auto-Track Discoveries

When you discover a bug, tech debt, or enhancement during work:
- Add it to `specs/backlog/backlog.md` immediately with appropriate priority
- Mention it to the user: "I found [issue] and added it as [ID] to backlog"

### Rule 4: Pre-Phase Bug Check

Before starting work on a new phase:
- Scan `specs/backlog/backlog.md` for P0/P1 bugs
- If any exist, recommend addressing them first
- Present: "N open bugs (X critical), recommend fixing before proceeding"

### Rule 5: Phase Boundary Awareness

When completing the last task in a phase:
- Prompt the user: "All tasks in Phase N are complete. Run `/complete-phase` to verify and release?"
- Do NOT auto-complete a phase without user confirmation

### Rule 6: Git Lifecycle (Automatic)

#### Starting Work
- **Before ANY code change**, check current branch
- If on `main` or `staging`, **auto-create a feature branch**:
  - Phase work: `phase-N-shortname`
  - Bug fix: `fix/BUG-NNN-short-desc`
  - Feature: `feat/short-desc`
  - Tech debt: `refactor/TD-NNN-short-desc`

#### During Work
- **Auto-commit** after each logical unit with conventional commits:
  - `feat(scope):` | `fix(scope):` | `docs:` | `refactor(scope):` | `chore:` | `infra:`
- Keep commits atomic — one logical change per commit
- Push to remote after significant milestones

#### Completing Work
- Commit all remaining changes, push branch
- **ASK the user** before merging to `staging` or `main`

| Action | Auto? | Requires Approval? |
|--------|-------|--------------------|
| Create feature branch | Yes | No |
| Commit to feature branch | Yes | No |
| Push feature branch | Yes | No |
| Delete merged feature branch | Yes (after confirmed merge) | No |
| Merge to `staging` | No | **Yes** |
| Merge to `main` | No | **Yes** |
| Tag a release | No | **Yes** |

### Rule 7: Plan Before Implementing

For any non-trivial implementation (new feature, architectural change):
- Use `/brainstorm-phase` to design the approach first
- Present the plan for user approval before making changes

### Rule 8: Record Phase History

During any active phase, append meaningful changes to `specs/phases/<active-phase>/history.md`.

#### What counts as "meaningful"

| Trigger | Entry type |
|---|---|
| ADR was created or its status/decision changed | `[DECISION]` |
| Phase scope was added to or reduced | `[SCOPE_CHANGE]` |
| Bug, tech debt, or enhancement was added to backlog | `[DISCOVERY]` |
| New feature was added to the phase plan | `[FEATURE]` |
| Architectural pattern or integration approach changed | `[ARCH_CHANGE]` |
| Locked evaluator was defined or its evaluation set changed | `[EVALUATOR]` |
| Anything else worth a future reader's time | `[NOTE]` |

After writing a history entry, check `specs/decisions/impact-map.json` and add any new topics so `/sync-docs` can find affected files.

#### Format (APPEND ONLY)

```
### [TYPE] YYYY-MM-DD — Short title
Topics: topic-1, topic-2
Affects-phases: phase-N-name (or "none")
Affects-specs: path/to/file.md#section (or "none")
Detail: One to three sentences describing what changed and why.

---
```

### Rule 9: Doc Sync Protocol — Never Mid-Phase, Always at Completion

- **During a phase**: Record to history. Do NOT update other specs.
- **At phase completion**: Run `/sync-docs` BEFORE `/complete-phase`.

### Rule 10: Architecture Specs Stability (monorepo)

Files under `specs/architecture/` are constitutional documents.

**During phase implementation:**
- READ specs as stable reference
- NEVER modify them based on implementation discoveries
- Log all gaps and changes as `[ARCH_CHANGE]` in phase history

**At phase completion (via `/sync-docs`):**
- **Additive changes** — update specs directly, no ADR required
- **Decisional changes** — ADR amendment FIRST, then spec update

### Rule 11: Evaluator Discipline — Lock Evaluators Before Loops

Before building any learning, optimization, or self-improvement loop:

1. Define the **evaluation set** — a fixed corpus with known-good outputs
2. Define the **scalar** — a single number that improves or doesn't
3. Commit the evaluator to `tests/benchmarks/` with a version tag
4. Build the loop **AFTER** the evaluator is committed
5. **NEVER** change the evaluator while the loop is being optimized

### Rule 12: Verify Before Claim — No Completion Without Evidence

Before claiming any task, fix, or implementation is "done":

1. Run the actual verification command (test, lint, typecheck, smoke test, build)
2. Read the output — both exit code and content
3. If the output isn't fresh from this attempt in this session, treat the task as unverified
4. Only mark a task `[x]` after a verification command produced passing output in this session

---

## Naming Conventions

### Backlog IDs
| Type | Prefix | Example |
|------|--------|---------|
| Bug | `BUG-` | `BUG-001` |
| Feature | `FEAT-` | `FEAT-001` |
| Tech Debt | `TD-` | `TD-001` |
| Enhancement | `ENH-` | `ENH-001` |

### Priorities
| Level | Meaning | SLA |
|-------|---------|-----|
| `P0` | Critical — blocks current phase | < 1 day |
| `P1` | High — current/next phase | < 1 week |
| `P2` | Medium — within 2 phases | < 1 phase |
| `P3` | Low — nice to have | best-effort |

### Git Branches
| Type | Pattern |
|------|---------|
| Phase | `phase-N-shortname` |
| Feature | `feat/description` |
| Bug fix | `fix/description` |
| Refactor | `refactor/description` |
| Infrastructure | `infra/description` |

### Git Commits (Conventional)
`feat:` | `fix:` | `docs:` | `refactor:` | `chore:` | `infra:`

Use `infra:` for CI, build, deploy, tooling, and release-pipeline changes.

---

## Constraints

1. **No secrets in code** — all credentials via env vars or AWS Secrets Manager
2. **Never commit to main** — always use feature/phase branches
3. **Plan before implementing** — use `/brainstorm-phase` for non-trivial work
4. **PII/PHI never travels raw** — must be scrubbed in Doc Processing before any downstream service
5. **HIPAA compliance is non-negotiable** — audit log every query, mask all patient data

---

## Project Extensions

> Everything below this heading is preserved across `momentum upgrade`.
> Add project-specific navigation, rules, cross-repo references, etc. here.
> Anything above this heading is managed by momentum and may be replaced on upgrade.

### Healthcare-Specific Rules

**Rule HC-1: PII Scrubbing is Always in Scope**  
Any task touching the Doc Processing service must include verification that PII scrubbing runs before any text is forwarded downstream. This is not optional.

**Rule HC-2: Audit Log is Always On**  
The Chat Service must write to `query_history` for every request — even errors. The compliance team audits this table. Never add a code path that skips the audit write.

**Rule HC-3: HIPAA Evaluations in Phase 5**  
All work in Phases 0–4 should be written with HIPAA in mind, but the formal HIPAA compliance audit happens in Phase 5. Do not claim HIPAA compliance before Phase 5 is complete.
