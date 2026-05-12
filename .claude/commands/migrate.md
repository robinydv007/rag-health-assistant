Onboard an existing project with a manual or outdated momentum-like structure into proper momentum format.

This command fills gaps without overwriting anything the project already has.

## Steps

1. **Detect existing structure** — scan for what momentum expects vs what is present:

   | Item | Expected path | Present? |
   |------|--------------|---------|
   | Spec root | `specs/` | |
   | Status file | `specs/status.md` | |
   | Backlog | `specs/backlog/backlog.md` | |
   | Phase index | `specs/phases/index.json` | |
   | Decisions dir | `specs/decisions/` | |
   | Planning dir | `specs/planning/` | |
   | Changelog dir | `specs/changelog/` | |
   | Agent rules | `.agent/rules/project.md` | |
   | Hook script | `scripts/check-history-reminder.sh` | |
   | Claude commands | `.claude/commands/` | |

   For `.claude/commands/`, list which of the standard momentum commands are missing:
   `brainstorm-idea`, `brainstorm-phase`, `start-project`, `start-phase`, `complete-phase`,
   `log`, `sync-docs`, `track`, `migrate`, `validate`

2. **Report gap summary** — present findings before making any changes:
   ```
   Found: 8 / Missing: 4 items
   Will add:
     - specs/backlog/details/ (.gitkeep)
     - specs/phases/index.json
     - .claude/commands/validate.md
     - .claude/commands/migrate.md
   Will skip (already exist):
     - specs/status.md
     - specs/backlog/backlog.md
     - .agent/rules/project.md
   ```
   Ask the user to confirm before proceeding.

3. **Fill gaps (skip-if-exists for all files)**:
   - Copy any missing momentum template files from `specs-templates/` — never overwrite
     files the project already has
   - Add any missing momentum commands to `.claude/commands/` — skip ones already present
   - Add `.agent/rules/project.md` if absent
   - Add `scripts/check-history-reminder.sh` if absent (and chmod +x)

4. **Phase index reconciliation** — if `specs/phases/index.json` is missing or its
   `phases` object is empty:
   - Scan `specs/phases/` for existing subdirectories (any `phase-*` directory)
   - Add each discovered phase to `index.json` with:
     ```json
     "<phase-dir-name>": { "status": "unknown", "topics": [] }
     ```
   - Inform the user: "Added N phases to index.json with status 'unknown' — update
     status and topics fields manually to match actual state"

5. **Report result**:
   ```
   ✓ Migration complete.
   Added: 4 items
   Skipped: 6 items (already existed — not overwritten)
   Needs manual attention:
     - specs/phases/index.json: 3 phases added with status 'unknown' — verify manually
     - specs/status.md: already exists — verify Current Phase matches index.json
   ```
