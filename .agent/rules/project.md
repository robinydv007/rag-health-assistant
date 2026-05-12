# Project Rules

## Navigation (Where to Find Things)

| Question | File |
|----------|------|
| Current state / what phase? | `specs/status.md` |
| What's in the backlog? | `specs/backlog/backlog.md` |
| Phase tasks/progress? | `specs/phases/phase-N-*/tasks.md` |
| Why was X chosen? | `specs/decisions/NNNN-*.md` |
| Roadmap / timeline? | `specs/planning/roadmap.md` |

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
- Auto-commit after each logical unit with conventional commits (`feat`/`fix`/`docs`/`refactor`/`chore`/`infra`)
- Never auto-merge to staging or main — always ask user
- Delete merged feature branches once confirmed merged

**Red Flags (STOP and switch branches):**
- "Just one commit to main" — branch first, decide later
- "I'll create the branch after these edits" — branch is non-optional
- "--no-verify just this once" — fix the underlying check
- "Force push is fine" — `--force-with-lease` minimum

### Rule 7: Plan Before Implementing
For non-trivial work: use `/brainstorm-phase` first.

### Rule 8: Record Phase History
Append to `specs/phases/<active-phase>/history.md` after meaningful changes.

**Trigger → Entry type:**
- ADR created/changed → `[DECISION]`
- Scope added/reduced → `[SCOPE_CHANGE]`
- Backlog item added → `[DISCOVERY]`
- Feature added to plan → `[FEATURE]`
- Architecture pattern changed → `[ARCH_CHANGE]`
- Locked evaluator defined or changed → `[EVALUATOR]`
- Anything else worth a future reader's time → `[NOTE]`

After writing an entry: update `specs/decisions/impact-map.json` with new topics.

The hook script `scripts/check-history-reminder.sh` runs after edits as a safety net.

Format (APPEND ONLY):
```
### [TYPE] YYYY-MM-DD — Short title
Topics: topic-1, topic-2
Affects-phases: phase-N-name (or "none")
Affects-specs: path/to/file.md#section (or "none")
Detail: One to three sentences.

---
```

**Red Flags (STOP and log):**
- "I'll write history at phase end" — you won't remember the *why*
- "Not important enough to log" — log it or revert it
- "It's in the commit message" — history is canonical

### Rule 9: Doc Sync Protocol
- During a phase: record to history only. Do NOT update other specs.
- At phase completion: run `/sync-docs` BEFORE `/complete-phase`.

**Multi-repo projects only:** NEVER modify docs in another repo. If a history `Affects-specs:` path starts with `../`, leave that file alone and flag the cross-repo impact to the user with the exact path. Cross-repo doc ownership is structural — never quietly change docs you don't own.

### Rule 10: Architecture Specs Stability (monorepo only)
Files under `specs/architecture/` are constitutional documents.

**During phase implementation:** READ specs as stable reference; NEVER modify them; log gaps as `[ARCH_CHANGE]` with `Affects-specs:`.

**At phase completion (`/sync-docs`):**
- **Additive changes** (new fields, new ports, extending an existing design) → update specs directly, no ADR
- **Decisional changes** (approach changes, design direction shifts) → ADR amendment FIRST, then spec update

**Red Flags (STOP and route correctly):**
- "Just one field, not a real change" — additive: fine at completion, not now
- "Faster to fix the spec than log the gap" — catastrophic globally
- "Spec is wrong, code is right, update spec" — only after an ADR

### Rule 11: Evaluator Discipline — Lock Evaluators Before Loops
Before building any learning/optimization loop:
1. Define the evaluation set (fixed corpus with known-good outputs)
2. Define the scalar (single number that improves or doesn't)
3. Commit the evaluator to `tests/benchmarks/` with a version tag
4. Build the loop AFTER the evaluator is committed
5. NEVER change the evaluator while the loop is being optimized

**Red Flags (STOP and freeze):**
- "Just one tweak to the eval so this run looks better" — exactly the failure mode
- "Lock the evaluator after we know what works" — you can't know without a lock
- "The eval doesn't measure what we care about" — version-bump to v2; don't mutate v1

If the eval set or scorer needs changes mid-loop, version-bump the evaluator. Never mutate the locked version.

### Rule 12: Verify Before Claim
Before marking any task `[x]`, run the verification command (test, lint, typecheck, smoke, build) and read its output. Fresh evidence in this session — not confidence, not similar-earlier-tests, not "looks right" — is the only signal of completion.

**Red Flags (STOP and run the verification):**
- "I'm confident this works" — confidence is not evidence
- "The change is too small to test" — "small" is the most common regression predicate
- "I'll batch verifications at the end" — you won't know which change broke what
- "Unit tests pass" — unit tests miss wiring bugs; run the integration path too

**Anti-rationalization:**
- "The diff is obviously correct" — diffs lie when context is incomplete
- "Type checking passed" — types catch shape errors, not behavior
- "CI will catch it" — CI catches it AFTER you claimed done

If verification was not run in this session, the task is unverified — leave it `[/]` (in progress). If a command can't run in the current environment, say so explicitly — never silently downgrade to "looks correct".

---

## Naming Conventions

Backlog IDs: `BUG-NNN` | `FEAT-NNN` | `TD-NNN` | `ENH-NNN`

Priorities (with SLA):
- P0 (critical, < 1 day)
- P1 (high, < 1 week)
- P2 (medium, < 1 phase)
- P3 (low, best-effort)

Branches: `phase-N-name` | `feat/desc` | `fix/desc` | `refactor/desc` | `infra/desc`

Commits: `feat:` | `fix:` | `docs:` | `refactor:` | `chore:` | `infra:` (CI/build/deploy/tooling)

---

## Project Extensions

> Everything below this heading is preserved across `momentum upgrade`.
> Add project-specific agent rules here. Anything above is managed by momentum.
