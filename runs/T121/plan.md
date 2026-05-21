Now I have everything I need. Here is the implementation plan:

---

## Objective

Fix `daemon_manager.py` to resolve runtime paths through `runtime_resolver` (so PID file, log file, and worktrees dir all point to the canonical `AI_DEV_FACTORY_RUNTIME_ROOT` when set), and expose a `POST /daemon/sync-main` endpoint with a matching UI button so the dashboard can serve as the primary runtime control surface.

## Included

### `services/control_api/services/daemon_manager.py`

- Import `resolve_runs_dir`, `resolve_logs_dir`, `resolve_worktrees_dir` from `..services.runtime_resolver`.
- Replace `_pid_path(project_root)` body: `return resolve_runs_dir(project_root) / _PID_FILENAME` (currently hardcoded to `project_root / "runs" / …`).
- Replace `_log_path(project_root)` body: `return resolve_logs_dir(project_root) / _LOG_FILENAME`.
- Replace `_current_ticket(project_root)` scan target: `runs = resolve_runs_dir(project_root)`.
- In `start()`, replace the `--worktrees-dir` argument from `str(project_root / "worktrees")` to `str(resolve_worktrees_dir(project_root))`.
- In `start()`, add `log.parent.mkdir(parents=True, exist_ok=True)` before opening the log file (logs dir may not exist on first run when `AI_DEV_FACTORY_RUNTIME_ROOT` is set).
- Add `sync_main(project_root: Path) -> ActionResult`: runs `git fetch origin main` (no checkout) in `project_root`, returns `ActionResult(ok=True/False, message=…)`.

### `services/control_api/routes/daemon.py`

- Add `POST /daemon/sync-main` endpoint that calls `daemon_manager.sync_main(_root(request))` and returns `ActionResult`.

### `apps/dashboard/src/api/daemon.js`

- Add `export const syncMain = () => client.post('/daemon/sync-main')`.

### `apps/dashboard/src/pages/DaemonPage.jsx`

- Import `syncMain` from `../api/daemon`.
- Add a "Sync Main" `ActionButton` alongside the existing Start/Stop/Restart buttons (same row, `variant="secondary"`), with `onSuccess={fetchStatus}`.

## Excluded

- WebSocket / SSE streaming for the activity feed (polling is functional).
- Any changes to `run_daemon.py`, `worktree_manager.py`, or other daemon internals.
- `routes/issues.py` intake-status stub (tracked separately).
- Multi-project orchestration.
- Dashboard layout or mobile responsiveness changes.
- Ticket log viewer changes (already routed correctly through `artifact_reader` + `runtime_resolver`).

## Acceptance criteria

- `GET /daemon/status` returns the running daemon's real PID when `AI_DEV_FACTORY_RUNTIME_ROOT` is set (reads from `$AI_DEV_FACTORY_RUNTIME_ROOT/runs/daemon.pid`).
- `GET /daemon/activity` returns lines from `$AI_DEV_FACTORY_RUNTIME_ROOT/logs/daemon.log` (not `<project_root>/runs/daemon.log`) when `AI_DEV_FACTORY_RUNTIME_ROOT` is set.
- `POST /daemon/start` launches the daemon with `--worktrees-dir` pointing to `$AI_DEV_FACTORY_RUNTIME_ROOT/worktrees` when the env var is set.
- `POST /daemon/start` succeeds even when `$AI_DEV_FACTORY_RUNTIME_ROOT/logs/` does not yet exist (dir is created automatically).
- `POST /daemon/sync-main` returns `ok: true` and a success message when `git fetch origin main` succeeds in the project root.
- `POST /daemon/sync-main` returns `ok: false` with the stderr content when the fetch fails.
- A "Sync Main" button appears in the Daemon page, calls the endpoint, and shows inline feedback via the existing `ActionButton` error/success display.
- All other dashboard actions (Start, Stop, Restart, Approve Plan, Run Next, Archive) continue to function without regression.
