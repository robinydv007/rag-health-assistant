Check the spec structure health of the current momentum project.

Run with no arguments for a fast index-first check, or pass `--deep` for a full scan.

## Default Mode (index-first)

1. Read `specs/status.md` — verify required fields are present:
   - `Last Updated`, `Current Phase`, `Latest Release`, `Health`
   - Active Phase table exists with at least one row
   - Report any missing fields as failures

2. Read `specs/backlog/backlog.md` — verify all 4 section tables present:
   - Bugs, Features, Tech Debt, Enhancements
   - Report any missing table as a failure

3. Read `specs/phases/index.json` — for each phase listed:
   - Verify directory exists at `specs/phases/<phase-id>/`
   - Verify all 4 files present: `overview.md`, `plan.md`, `tasks.md`, `history.md`
   - Report missing directories or files as failures

4. Cross-check active phase consistency:
   - Active phase in `status.md` must be listed in `index.json`
   - Its directory must exist
   - Report mismatch as a failure

5. Check `.claude/commands/` for standard momentum commands:
   - Required: `brainstorm-idea`, `brainstorm-phase`, `start-project`, `start-phase`,
     `complete-phase`, `log`, `sync-docs`, `track`, `migrate`, `validate`
   - Report any missing commands as warnings (not failures — project may predate them)

6. Report results:
   ```
   ✓ N checks passed
   ✗ N issues found:
     - specs/phases/index.json: phase-3-gap-fixes directory missing
     - specs/status.md: missing field "Latest Release"
   ```

## `--deep` Flag (full scan)

Run all default mode checks, then additionally:

7. Walk ALL directories under `specs/phases/` — flag any directory not listed in
   `index.json` as an orphaned phase

8. For each phase directory, read `tasks.md`:
   - Extract all backlog ID references: `BUG-NNN`, `FEAT-NNN`, `TD-NNN`, `ENH-NNN`
   - Verify each ID exists as a row in `specs/backlog/backlog.md`
   - Report unresolved IDs as failures

9. For each phase directory, read `history.md`:
   - Verify each entry has all required fields: type tag `[TYPE]`, date in `YYYY-MM-DD`
     format, `Topics:`, `Affects-phases:`, `Affects-specs:`, `Detail:`
   - Report malformed entries (missing fields) as warnings

10. Check `specs/changelog/` — for each phase with status `complete` in `index.json`,
    verify at least one changelog file exists under `specs/changelog/`
    - Report completely absent changelog as a warning

11. Append deep-scan results to the report before printing.
