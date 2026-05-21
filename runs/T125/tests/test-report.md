I have all the information needed for a complete validation. Here is the test report.

---

# Test Report — T125: Project-Scoped Runtime APIs and Daemon Isolation

## Test execution

```
18 passed in 0.76s
```

Both test suites pass cleanly: `test_project_isolation.py` (9 tests) and `test_project_scoped_routes.py` (9 tests).

---

## Acceptance criteria

### AC1 — Runtime actions only affect the selected project
**PASS**

All project-scoped action endpoints (`/projects/{id}/daemon/start`, `.../stop`, `.../restart`, `.../tickets/{id}/run-next`, etc.) receive `project_root` via `Depends(resolve_project)` and pass it directly to service calls. An unknown `project_id` returns HTTP 404 before any service code executes. There is no path by which an action on project A could affect project B.

---

### AC2 — Logs, workers and queues are isolated per project
**PASS**

`daemon_manager` routes every artifact (PID file, log file, workers.json, retry-state.json) through `resolve_runs_dir(project_root)`, `resolve_logs_dir(project_root)`, and `resolve_state_dir(project_root)`. Unit tests (`test_daemon_activity_reads_only_given_project`, `test_runtime_status_reads_only_given_project`) confirm that writing to project-A's log does not appear in project-B's activity response, and project-A's queue entries do not appear in project-B's runtime status.

**Known limitation:** When `AI_DEV_FACTORY_RUNTIME_ROOT` is set, `resolve_runs_dir` and `resolve_logs_dir` return a single shared directory (`$RUNTIME_ROOT/runs`, `$RUNTIME_ROOT/logs`) regardless of which `project_root` is passed. This collapses per-project isolation. The test suite explicitly unsets this variable (`monkeypatch.delenv`), so the tests cannot catch this scenario. This env var is a carry-over from T123/T124 single-project mode and should not be set in a multi-project deployment, but this constraint is undocumented. Not blocking for stated T125 scope (multi-project mode via `AI_DEV_FACTORY_PROJECTS_ROOT`), but a documentation gap.

---

### AC3 — Project-scoped runtime endpoints return only project-specific data
**PASS**

Integration tests confirm:
- `GET /projects/project-a/tickets` returns T001, T002; `GET /projects/project-b/tickets` returns `[]` when only project-A has tickets.
- `GET /projects/project-b/tickets/T001` returns 404 when T001 belongs to project-A.
- `GET /projects/project-a/daemon/runtime-status` shows T001 in intake queue; project-B's endpoint does not.
- Unknown project IDs return 404 across daemon, tickets, and project-map endpoints.

---

### AC4 — Switching project refreshes dashboard runtime state correctly
**PASS**

`usePolling(callback, delay, key)` at `apps/dashboard/src/hooks/usePolling.js:14` has `[delay, key]` as its effect dependency. When `activeProject` changes in `App.jsx`, it is passed as the `key` argument to all `usePolling` calls in `DaemonPage`, `TicketsPage`, and `ProjectMapPage`. The effect immediately calls the callback and restarts the polling interval, guaranteeing a fresh fetch with the new `projectId`.

---

### AC5 — Existing single-project workflows continue to function
**PASS**

Legacy routes (`/daemon/status`, `/daemon/start`, `/tickets`, etc.) are preserved in `router` (separate from `project_router`) and continue to use `app.state.project_root`. Two dedicated integration tests confirm: `test_legacy_daemon_status_still_works` and `test_legacy_tickets_still_works`.

---

### AC6 — Tests validate project isolation with multiple runtime roots
**PASS**

`test_project_isolation.py`: 9 unit tests directly instantiate services with two separate `tmp_path` subdirectories as `project_root`. Covers `runtime_resolver` dir separation, `daemon_manager` status/activity/runtime-status, and `artifact_reader` list/get/logs.

`test_project_scoped_routes.py`: 9 integration tests spin up a full FastAPI app with two project roots via `create_app(project_root=proj_a, projects_root=tmp_path)`. Covers HTTP routing isolation, 404 enforcement, and legacy route compatibility.

---

### AC7 — Runtime artifacts no longer duplicated across unrelated worktrees or projects
**PASS**

`artifact_reader.list_tickets(project_root)` only scans `resolve_runs_dir(project_root)` and the per-project `worktrees_dir` (computed as `project_root.parent / (project_root.name + "-worktrees")` in local mode). `get_ticket(project_root, ticket_id)` returns `None` if the ticket's `state.json` is not found under that project root, tested directly by `test_get_ticket_returns_none_for_wrong_project`. Cross-project ticket leakage at the API layer is eliminated.

---

## Summary

| Criterion | Status |
|---|---|
| Runtime actions only affect the selected project | **PASS** |
| Logs, workers and queues are isolated per project | **PASS** |
| Project-scoped endpoints return only project-specific data | **PASS** |
| Switching project refreshes dashboard runtime state | **PASS** |
| Existing single-project workflows continue to function | **PASS** |
| Tests validate project isolation with multiple runtime roots | **PASS** |
| Runtime artifacts no longer duplicated across unrelated projects | **PASS** |

**18/18 tests pass. All acceptance criteria met.**

One non-blocking documentation gap: when `AI_DEV_FACTORY_RUNTIME_ROOT` is set, per-project runtime isolation is silently bypassed because `runtime_resolver` maps all projects to the same shared directory. This constraint should be documented — it is incompatible with multi-project deployment and the test suite avoids it via `monkeypatch.delenv`.

**Verdict: IMPLEMENTATION APPROVED** with the documentation gap noted above as a follow-up recommendation.
