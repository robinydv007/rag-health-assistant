Begin a new implementation phase.

## Steps

1. Read current state:
   - Read `specs/status.md`

2. Check for blocking bugs (pre-phase bug check):
   - Scan `specs/backlog/backlog.md` for P0/P1 items
   - If P0 bugs exist → report to user, recommend fixing first
   - If only P1 → continue but note them

3. Create the phase directory if it doesn't exist:
   ```
   specs/phases/phase-N-shortname/
   ├── overview.md    ← Scope, goals, deliverables, acceptance criteria
   ├── plan.md        ← Implementation approach with group execution pattern
   ├── tasks.md       ← Granular checklist [ ] / [x]
   └── history.md     ← Append-only log
   ```
   Use `/brainstorm-phase` first if these files don't exist yet.

   Note: if running `/start-phase` without `/brainstorm-phase` first, create
   `history.md` now — an empty append-only log with the entry-types header table.

4. Build phase topic index:
   - Read the phase's `overview.md` and `tasks.md`
   - Extract key topics: technology names, services, architectural concepts
   - Add/update the phase entry in `specs/phases/index.json`:
     ```json
     "phase-N-name": {
       "status": "in-progress",
       "topics": ["topic-1", "topic-2"]
     }
     ```

5. Update `specs/phases/README.md`:
   - Change phase status: `Not Started` → `In Progress`

6. Update `specs/status.md`:
   - Set "Current Phase" to the new phase
   - Update "Active Phase" table
   - Clear/update blockers

7. For monorepo only — identify relevant architecture specs:
   - Check `specs/planning/release-plan.md` for this phase's deliverables
   - List which specs in `specs/architecture/` are relevant
   - Note them in the phase's `plan.md` under "Reference Specs"

8. If this phase requires a locked evaluator (learning/optimization loop):
   - Add "Lock [Evaluator]" as the FIRST task in `tasks.md`

9. Create git branch and initial commit:
   ```bash
   git checkout main && git pull origin main
   git checkout -b phase-N-shortname
   git add specs/
   git commit -m "docs: start Phase N - {phase name}"
   git push -u origin phase-N-shortname
   ```

10. Update `specs/changelog/YYYY-MM.md` with phase start entry.
