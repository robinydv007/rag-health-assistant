Verify, finalize, and release a completed phase.

## Steps

### Verify

1. Read the phase's acceptance criteria:
   - Read `specs/phases/phase-N-*/overview.md`

2. Verify all tasks are done:
   - Read `specs/phases/phase-N-*/tasks.md`
   - If any `[ ]` unchecked items remain → report to user, do NOT proceed

3. **Run project-specific validation and capture fresh evidence** (per Rule 12 — Verify Before Claim):
   - Run all defined validation commands: tests, linting, type checks, build, smoke tests
   - Capture each command's stdout/stderr (e.g., redirect to a temp file with `tee`)
   - Note exit codes
   - If any command fails → STOP, report failure to user, do NOT proceed to Finalize
   - If a command can't run in the current environment, say so explicitly — do not silently skip

   **Refuse to advance to Finalize without fresh, captured evidence.** Memory of "tests passed earlier this phase" is not evidence — re-run them now.

4. If this phase built a learning loop, verify:
   - Locked evaluator exists in `tests/benchmarks/`
   - Convergence measurement logged (scalar improved)
   - If not → report to user, do NOT proceed

5. Check for new bugs discovered during the phase:
   - Grep `specs/backlog/backlog.md` for items tagged to this phase

### Finalize

**Step F0: Sync docs from phase history (run BEFORE other finalize steps)**
- Run `/sync-docs` to propagate all history-recorded changes to relevant documents
- If /sync-docs finds nothing to update, proceed directly

6. Create retrospective:
   - `specs/phases/phase-N-*/retrospective.md`
   - What went well, what didn't, lessons learned
   - **Append a `## Verification Evidence` section** with the captured output from Step 3:
     - For each validation command: command line, exit code, last 50 lines of output (or full output if shorter)
     - Format as fenced code blocks with the command as the heading
     - This is the durable record that Rule 12 was honored — it must exist before the release section runs

7. Update all tracking:
   - `specs/phases/README.md` → mark `Complete`
   - `specs/status.md` → update current phase to next, add release version
   - `specs/planning/roadmap.md` → update phase status
   - `specs/changelog/YYYY-MM.md` → add release entry

### Release

> **Gate (Rule 12):** Do NOT enter Release if `retrospective.md` lacks a `## Verification Evidence` section. If evidence is missing, return to Step 3 and capture it.

8. Commit all remaining changes and push:
   ```bash
   git add -A
   git commit -m "docs: complete Phase N - {phase name}"
   git push origin phase-N-shortname
   ```

9. Ask the user ONCE for approval to release — present the full plan:
   ```
   Ready to release vX.Y.Z. This will:
     1. Merge phase-N-shortname → staging
     2. Merge staging → main
     3. Tag vX.Y.Z and create GitHub Release

   Proceed?
   ```
   Wait for a single "yes" before running any of the following steps.

10. On approval, execute all three steps in sequence:

    ```bash
    # step 1 — phase branch → staging
    git checkout staging && git pull origin staging
    git merge --no-ff phase-N-shortname -m "merge: phase-N-shortname → staging (vX.Y.Z)"
    git push origin staging

    # step 2 — staging → main
    git checkout main && git pull origin main
    git merge --no-ff staging -m "merge: staging → main (vX.Y.Z — Phase N: {phase name})"
    git push origin main

    # step 3 — tag + GitHub Release
    git tag -a vX.Y.Z -m "Phase N: {phase name}"
    git push origin vX.Y.Z
    gh release create vX.Y.Z \
      --title "vX.Y.Z — Phase N: {phase name}" \
      --notes "## Phase N: {phase name}
    {bullet summary of what was delivered}
    ### Next: Phase N+1 — {next phase name}" \
      --target main
    ```

12. Report summary to user:
    - What was delivered
    - GitHub Release URL
    - What's next
    - Remind to delete phase branch: `git push origin --delete phase-N-shortname`
