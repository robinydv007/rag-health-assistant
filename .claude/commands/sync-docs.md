Sync all relevant documents based on the active phase's history log.
Token-efficient: reads history + 2 tiny indexes first, then only targeted files.

## Steps

### Step 1: Load history and indexes (cheap reads)
- Read `specs/status.md` → identify active phase
- Read `specs/phases/<active-phase>/history.md` → extract all entries
- Read `specs/phases/index.json` (~2KB)
- Read `specs/decisions/impact-map.json` (~3KB)

### Step 2: Build targeted file list
For each history entry:
  - Extract Topics list
  - Look up each topic in index.json → collect affected phase tasks.md files
  - Look up each topic in impact-map.json → collect affected spec files/sections
  - Deduplicate the combined list
  - For monorepo: EXCLUDE files in `specs/architecture/`
    (constitution — never auto-synced, only amended via formal process)
  - **Multi-repo: PARTITION OUT cross-repo entries.** If a history entry has an
    `Affects-specs:` path starting with `../` (or otherwise outside this repo),
    add it to a separate "cross-repo" list. NEVER edit those files — you only
    own this repo's docs.

### Step 3: Show sync plan (ALWAYS show before touching anything)
Present to user:
  "Based on phase history, I will check and potentially update:
  - [list of files]
  Proceed? (yes/no)"

**If any cross-repo entries were partitioned out in Step 2:** also show them
under a "Cross-repo impact (NOT touching — sync the other repo manually)"
heading, listing each `Affects-specs: ../...` path. Tell the user which repo
they need to edit and which entries pointed there. Do NOT prompt for approval
on cross-repo paths — they're informational only.

If user says no → stop.

### Step 4: Read and assess (targeted reads only)
For each file in the list:
  - Read only the relevant section
  - Assess: does it need updating based on history entries?

### Step 5: Make updates (one at a time, fully visible)
For each file that needs updating:
  - Show the user what will change
  - Use the Edit tool to make the change

### Step 6: Update phase index if scope changed
If any [SCOPE_CHANGE] entries exist:
  - Update `specs/phases/index.json` for the active phase's topic list

### Step 7: Commit all changes
```bash
git add <all modified spec files>
git commit -m "docs(phase-N): sync specs from phase history"
```

### Step 8: Confirm completion
"Spec sync complete. Updated N files:
- [list]
Ready to run /complete-phase."

## Safeguards
- NEVER update files not in the targeted list
- NEVER update `specs/architecture/` (monorepo only — constitution is read-only)
- NEVER update files in another repo (paths starting with `../`) — you only own this repo's docs. Flag cross-repo entries to the user instead.
- ALWAYS show the plan (Step 3) before making any edits
- History entries are NEVER modified — only read
