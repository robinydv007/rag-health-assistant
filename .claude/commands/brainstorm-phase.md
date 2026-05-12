Brainstorm the next phase before creating it.

Run AFTER `/complete-phase` and BEFORE `/start-phase`.

## Important: No Separate Design Document

All output goes directly into the phase directory as standard phase files.
The brainstorm output IS the phase files — there is no intermediate design doc.

## Steps

1. Review current state:
   - Read `specs/status.md` — what phase just completed?
   - Read the completed phase's `history.md` — what was learned?
   - Read `specs/backlog/backlog.md` — any P0/P1 items to address first?

2. Check the roadmap:
   - Read `specs/planning/roadmap.md` — what's the next planned phase?
   - Is the planned phase still the right next step given what was learned?

3. Define scope with the user (one question at a time):
   - What is the goal of this phase?
   - What are the key deliverables?
   - What are the acceptance criteria?
   - What are the non-goals (explicitly out of scope)?

4. For monorepo — identify reference specs:
   - Which architecture docs in `specs/architecture/` are relevant?
   - Are there any spec gaps that need to be filled first?
   - If gaps exist, propose an ADR or addendum before proceeding.

5. Gap analysis (monorepo only):
   - Cross-reference brainstormed design against architecture specs
   - Verify interface counts, field names, error codes match exactly
   - Record findings and resolutions

6. Draft phase files directly:
   - `overview.md` — goal, key decisions table, scope (in/out), deliverables with verification commands, acceptance criteria
   - `plan.md` — full implementation plan using the Group Execution Pattern (see below)
   - `tasks.md` — granular checklist mirroring plan.md tasks
   - `history.md` — log all decisions and discoveries from this brainstorm session

7. Present for user approval:
   - Show key sections of overview.md and plan.md
   - Ask: "Does this look right? Any changes before we create the phase?"

8. On approval, write all files to `specs/phases/phase-N-shortname/` and commit:
   ```bash
   git add specs/phases/phase-N-shortname/
   git commit -m "docs: brainstorm Phase N — {phase name}"
   ```

9. Prompt: "Phase N is planned. Run `/start-phase` when ready to begin."

## Group Execution Pattern for plan.md

Declare the execution order at the top of every plan.md:

```
# Sequential:  Group 0 → Group 1 → Group 2
# Parallel:    (Groups 0 + 1 + 2 in parallel) → Group 3
# Mixed:       Group 0 → (Groups 1 + 2 in parallel) → Group 3
```

Every group header declares:
- `**Sequential.**` or `**Parallel with Groups X and Y.**`
- External dependencies (libraries, services, running processes)
- Commit message for the group

Standard layout:
- **Group 0** — contracts, types, migrations (sequential, blocks everything)
- **Middle groups** — independent feature areas (parallel candidates)
- **Second-to-last** — wiring and integration (sequential)
- **Last** — verification: tests, benchmarks, smoke tests (sequential)

## Key Principles
- One question at a time — don't overwhelm
- Each phase should be completable in a focused sprint
- If scope is too large, suggest splitting into sub-phases
- Record any discoveries in history.md
