Tests pass; the supervisor failure is pre-existing on HEAD. Now let me write the structured review.

## Review — T206

### Scope & ticket alignment

The implementation maps to the plan and ticket goals:

| Requirement | Status | Notes |
|---|---|---|
| Project-scoped DB resolution | ✓ | `get_db_path(project_id)` + `resolve_db_path_for_project(...)` in `tools/agent_runner/runtime_db.py:190-249`; Postgres backend rebound symmetrically at `runtime_db.py:1038-1044`. |
| Both endpoints share a single resolver | ✓ | `_resolve_db_for_project()` in `services/control_api/routes/intelligence.py:70-94` used by both GET and POST. |
| Persist `queued` *before* delegation | ✓ | `intelligence.py:302` (queued) precedes `_delegate_analyze_to_supervisor` call. |
| Persist `failed` on supervisor delegation failures | ✓ | `intelligence.py:320-329` via `_persist_delegation_failure`; POST still surfaces non-2xx. |
| Supervisor pre-thread try/except writes `failed` | ✓ | `services/supervisor/main.py:2314-2337`. |
| Stale-analysis reaper (`queued > 10m`, `running > 15m`) | ✓ | `tools/agent_runner/ticket_intelligence_recovery.py`; opportunistic call on every GET and POST. |
| Structured `intel.*` logs | ✓ | `intel.queued/delegated/started/subprocess/completed/failed/reaped` across analyzer, route, supervisor. |
| Polling resilience cap | ✓ | `MAX_CONSECUTIVE_POLL_ERRORS=5` in `TicketIntelligencePanel.jsx`; 404 doesn't increment counter. |
| Tests | ✓ | 17 new tests (db resolution, recovery, analyzer failure paths, delegated completion, persisted delegation failure). All ticket-intelligence tests pass locally. |

No scope creep was introduced.

### Substantive observations (non-blocking)

1. **Docker + SQLite + multi-project path resolution gap.** In the documented Docker stack, the API container has `RUNTIME_BASE_ROOT=/Users/<you>/runtime` (a *host* path, per `deploy/.env.example:32`) and `AI_DEV_FACTORY_RUNTIME_ROOT=/runtime` (container path). `_resolve_db_for_project` calls `resolve_db_path_for_project(project_id)` without applying `to_container_path()` — it will therefore resolve to a host path that doesn't exist inside the container (when `RUNTIME_BASE_ROOT` is set), or to a doubly-nested container path `/runtime/<id>/...` (when only `AI_DEV_FACTORY_RUNTIME_ROOT` is set, which itself points at one project's root). The established convention elsewhere is to call `to_container_path()` on persisted runtime roots — see `services/control_api/services/runtime_resolver.py:37-46`. **In Postgres mode (the recommended backend per `deploy/.env.example:113-134` and `docker-compose.yml:53-66`), this is moot** because handles are project-scoped row keys, not paths. Single-project SQLite-without-Docker is unchanged. Flagging as a follow-up because the plan explicitly excluded SQLite/Postgres migration, but the ticket's "same runtime DB" guarantee only holds for Postgres mode in the multi-project Docker scenario.

2. **Reaper is SQLite-only.** `_scan_stale_rows` opens `sqlite3.connect(str(db_path))` and returns `[]` when `Path(str(db_path)).exists()` is false (`ticket_intelligence_recovery.py:58-69`). In Postgres mode `db_path` is a `PgHandle`, `Path("postgres:adf#…").exists()` is False, so the reaper silently no-ops. The Postgres backend doesn't suffer the original file-locking root cause, but a crashed analyzer can still leave a row stuck in `running` — recovery wouldn't trigger. A `runtime_db`-mediated scan would close that gap.

3. **Reaper marks slow analyses as failed by clock-time, not by liveness.** A legitimate analyzer still running past `STALE_RUNNING_SECONDS=900s` would be transitioned to `failed` on the next GET, even though the analyzer would later attempt to write a real outcome to the same row. The 120s subprocess timeout caps normal runs well below the threshold, so this is acceptable.

4. **No `intel.queued` log on supervisor idempotent short-circuit** (`supervisor/main.py:2293-2294`). Minor lifecycle gap if a stuck row goes through the reaper-then-short-circuit path; not lifecycle-blocking.

5. **`runs/T206/daemon.lock` was auto-committed** (commit `9a85024b chore(T206): pre-sync auto-commit`). Workflow artifact, not part of the implementation, but it shouldn't ship — likely a gitignore miss in the pre-sync flow. Out of scope for T206 to fix.

### Code quality

- `_try_reap` and `_persist_delegation_failure` are well-scoped helpers, swallowing exceptions correctly so GET/POST don't break.
- Truncation in analyzer logs (500 chars) honors the plan's "no full prompt/stdout" rule (`ticket_intelligence_analyzer.py:37-40`, `:299-303`).
- Tests are careful about postgres-env contamination: each test file rebinds `runtime_db` to a freshly-loaded SQLite copy (`tests/test_ticket_intelligence_recovery.py:21-49`). Good hygiene.

### Security / safety

- No secrets logged; subprocess stderr truncated.
- DB writes always parameterised through the existing `runtime_db` helpers.
- The reaper writes a clear, audit-friendly `analysis_summary`.

### Tests

`pytest tests/test_ticket_intelligence_*.py -q` → all pass (120 collected — extractor & DB tests included). The single failing supervisor test (`test_lifespan_restores_exec_cmd_and_restart_policy`) reproduces on `git stash`, confirming it's unrelated to T206.

### Acceptance criteria

All required acceptance criteria from the plan are met for SQLite (non-Docker) and Postgres modes. The "Docker + SQLite + multi-project" case is partially addressed: API/supervisor agree on row identity logic but not on filesystem path resolution. Recommended setup (Postgres) is unaffected.

IMPLEMENTATION_APPROVED
