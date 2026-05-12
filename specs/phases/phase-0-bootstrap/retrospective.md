# Phase 0 — Bootstrap Retrospective

> **Released**: 2026-05-12  
> **Version**: v0.1.0  
> **Duration**: 1 session  
> **Tasks**: 35 / 35

---

## What Went Well

- **Pre-phase review caught real gaps early.** A spec audit before opening the phase found two untracked ADRs, a gitignore misconfiguration that silently hid `shared/models/`, and a docker build-context bug. Fixing these upfront prevented late-phase surprises.
- **Shared models were clean on first write.** All 15 unit tests passed immediately with no iteration. Pydantic v2 + typed enums gave strong contracts from day one.
- **docker-compose self-initialization pattern worked.** Adding `db-migrate` and `weaviate-init` as one-shot services means the stack bootstraps automatically — no manual script steps for new engineers.
- **Monorepo build-context fix was a real win.** Changing all 6 service build contexts to the repo root (`../../`) unblocked the `COPY shared/` instruction. The fix is simple but would have stalled every Phase 1 service that imports shared models.

## What Didn't Go Well

- **gitignore masked `shared/models/` silently.** The rule `models/` matched `shared/models/` because it lacked a root anchor (`/models/`). The models appeared to exist on disk but were invisible to git. Caught by review, not by CI.
- **PAT lacked `workflow` scope.** Pushing `.github/workflows/ci.yml` was blocked until the token was updated. No error until push time.
- **Pip timeout in docker-compose.** The `db-migrate` service hit a `ReadTimeoutError` on first run downloading alembic — it recovered on retry, but the warning noise is concerning for CI environments with strict time limits.
- **Line-length lint failures at completion.** Four E501 errors in `weaviate_schema.py` and `test_config.py` were only caught at `/complete-phase` time, not during development. CI would have caught these, but the CI wasn't wired to the branch yet at that point.

## Lessons Learned

- Run `ruff check .` locally before pushing — don't assume the first-write is lint-clean.
- Keep `pip install` steps in docker-compose init services fast: pin exact versions or pre-bake a layer. Flaky package downloads are a reliability issue.
- The `/models/` vs `models/` gitignore distinction is subtle. Add a comment explaining the intent next to any root-anchored rule.

---

## Verification Evidence

### `ruff check .` — exit code 0

```
All checks passed!
```

### `pytest tests/ -v` — exit code 0

```
============================= test session starts =============================
platform win32 -- Python 3.13.9, pytest-8.4.2, pluggy-1.5.0
rootdir: D:\Development\Projects\ai\rag-health-assistant
configfile: pyproject.toml
collected 15 items

tests/test_config.py::test_base_settings_defaults PASSED                 [  6%]
tests/test_config.py::test_base_settings_optional_fields_are_nullable PASSED [ 13%]
tests/test_config.py::test_weaviate_chunk_class_structure PASSED         [ 20%]
tests/test_config.py::test_weaviate_schema_wrapper PASSED                [ 26%]
tests/test_models.py::test_document_record_defaults PASSED               [ 33%]
tests/test_models.py::test_document_create_auto_job_id PASSED            [ 40%]
tests/test_models.py::test_doc_type_enum_values PASSED                   [ 46%]
tests/test_models.py::test_document_status_progression PASSED            [ 53%]
tests/test_models.py::test_chunk_metadata_defaults PASSED                [ 60%]
tests/test_models.py::test_sqs1_message_serialization PASSED             [ 66%]
tests/test_models.py::test_sqs2_message_with_chunks PASSED               [ 73%]
tests/test_models.py::test_sqs3_message PASSED                           [ 80%]
tests/test_models.py::test_ask_request_optional_session PASSED           [ 86%]
tests/test_models.py::test_ask_request_with_session PASSED               [ 93%]
tests/test_models.py::test_source_citation_optional_fields PASSED        [100%]

============================= 15 passed in 0.10s ==============================
```

### `docker-compose up db-migrate` — exit code 0

```
db-migrate-1 | INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
db-migrate-1 | INFO  [alembic.runtime.migration] Will assume transactional DDL.
db-migrate-1 | INFO  [alembic.runtime.migration] Running upgrade  -> 0001, Initial schema: documents, query_history, indexing_jobs, chunk_audit
db-migrate-1 exited with code 0
```
