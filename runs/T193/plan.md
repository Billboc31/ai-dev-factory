Now I have a complete understanding of the architecture. Let me write the plan.

---

## Objective

Make ticket boards, runs, logs, and daemon lifecycle fully project-scoped by routing all data reads and daemon writes through the selected project's `project_runtime_root` instead of the shared global SQLite database and runtime directory.

## Included

### Root cause (board shows wrong tickets)

`board_service._try_load_runtime_db()` ignores `project_runtime_root` and always calls `mod.get_db_path()`, which returns a single global `{AI_DEV_FACTORY_RUNTIME_ROOT}/.runtime/ai-dev-factory.sqlite`. All projects share one DB; `list_ticket_runtime(db_path)` returns every ticket regardless of which project is queried.

**`services/control_api/services/board_service.py`**
- `_try_load_runtime_db(project_root, project_runtime_root=None)`: when `project_runtime_root` is provided, derive DB path as `project_runtime_root / ".runtime/ai-dev-factory.sqlite"`. If that path does not exist, skip SQLite entirely (do not fall back to the global DB). Load the module and return `(mod, per_project_db_path, False)`.
- `get_board(project_root, repo=None, worktrees_dir=None, project_runtime_root=None)`: add `project_runtime_root` parameter; forward it to `_try_load_runtime_db`.

**`services/control_api/routes/daemon.py`**
- `project_daemon_board`: already receives `project_runtime_root` via `Depends(resolve_project_runtime_root)`. Pass it to `board_service.get_board()`.

---

### Daemon writes to per-project database

When a daemon is started for a project, it must inherit `AI_DEV_FACTORY_RUNTIME_ROOT={project_runtime_root}` so it writes ticket state, workers, and issue intake to the project's own SQLite DB.

**`services/control_api/services/daemon_manager.py`**
- `start(project_root, exec_cmd, restart_policy, project_runtime_root=None)`: when `project_runtime_root` is provided, override `AI_DEV_FACTORY_RUNTIME_ROOT` in the subprocess env before `Popen`. Also call `runtime_db.init_runtime_db(project_runtime_root / ".runtime/ai-dev-factory.sqlite")` before spawning so the DB directory and tables exist.
- `restart(project_root, exec_cmd, restart_policy, project_runtime_root=None)`: forward `project_runtime_root` to `start()`.

**`services/control_api/routes/daemon.py`**
- `project_daemon_start`: add `project_runtime_root: Path | None = Depends(resolve_project_runtime_root)`; pass it to `daemon_manager.start()`.
- `project_daemon_restart`: same addition, forward to `daemon_manager.restart()`.

---

### Runs and logs isolation

The project-scoped ticket routes already use `resolve_worktrees_dir(project_root, project_runtime_root=project_runtime_root)` for worktree discovery. However, `artifact_reader.list_tickets(project_root, worktrees_dir=wt_dir)` internally calls `resolve_runs_dir(project_root)` without `project_runtime_root`, relying on the env-var formula `{AI_DEV_FACTORY_RUNTIME_ROOT}/{project_id}/runs`.

**`services/control_api/routes/tickets.py`**
- `project_list_tickets`, `project_get_ticket`, `project_get_state`, `project_get_logs`, and all other project-scoped ticket endpoints: compute `runs_dir = resolve_runs_dir(project_root, project_runtime_root=project_runtime_root)` explicitly and pass it to `artifact_reader` so the path is always authoritative rather than derived from the env formula.

Check that `artifact_reader.list_tickets`, `get_ticket`, `get_ticket_state`, `get_ticket_logs` accept an explicit `runs_dir` parameter (or `project_runtime_root`) and use it. Add/update the parameter if absent.

---

### Audit log per-project DB path

`tickets.py` uses `_db_path(request)` → `request.app.state.db_path`, which is a single global path set at startup. Project-scoped audit log writes on actions (approve, retry, etc.) should use the project's own DB.

**`services/control_api/routes/tickets.py`**
- In all project-scoped action endpoints (`project_approve_plan`, `project_retry`, etc.), derive `db_path = project_runtime_root / ".runtime/ai-dev-factory.sqlite"` when `project_runtime_root` is available instead of `_db_path(request)`.
- Keep the fallback to `_db_path(request)` for legacy routes.

---

### Tests

- `services/control_api/tests/` (existing test suite): add or update board tests to assert that `get_board()` called with a `project_runtime_root` pointing to a temporary per-project DB only returns tickets written to that DB, not tickets in a separate global DB.
- Add a test that `daemon_manager.start()` sets the correct `AI_DEV_FACTORY_RUNTIME_ROOT` env var in the spawned process when `project_runtime_root` is given.

---

## Excluded

- **Legacy routes** (`GET /tickets`, `GET /daemon/board` without `/projects/{id}` prefix): not called by the project-scoped UI; do not migrate.
- **Supervisor multi-project support**: the supervisor's `/daemon/start` and `/daemon/status` calls are project-unaware; fixing supervisor routing is a separate ticket.
- **UI changes**: the frontend already calls all project-scoped routes with the correct `projectId`; no frontend edits required.
- **Project selector / routing changes**: UI project switching and re-polling are already correct.
- **`run_daemon.py` and agent runner tools**: they read `AI_DEV_FACTORY_RUNTIME_ROOT` from the environment, which will be correctly set by the daemon start fix above; no changes needed in those files.

---

## Acceptance criteria

- Selecting `test-ai-dev` in the UI returns a board populated only from `{test-ai-dev runtime root}/.runtime/ai-dev-factory.sqlite`; tickets from `ai-dev-factory` are absent.
- Selecting `ai-dev-factory` in the UI returns its own board; tickets from `test-ai-dev` are absent.
- A daemon started for `test-ai-dev` via `POST /projects/test-ai-dev/daemon/start` spawns a process with `AI_DEV_FACTORY_RUNTIME_ROOT` set to the `test-ai-dev` runtime root, confirmed by checking the process env or the banner written to `daemon.log`.
- `GET /projects/test-ai-dev/tickets` lists only tickets whose run directories live under `test-ai-dev`'s `runs/` path.
- `GET /projects/test-ai-dev/tickets/{ticket_id}/logs` returns the log from `{test-ai-dev runtime root}/runs/{ticket_id}/runtime.log`, not from the ai-dev-factory runtime.
- No regression: `GET /projects/ai-dev-factory/daemon/board` continues to work and returns ai-dev-factory tickets.
- All existing control API tests pass.
