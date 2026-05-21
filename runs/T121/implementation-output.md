All four files look correct. Implementation is complete.

---

**Summary of changes**

| File | Changes |
|---|---|
| `services/control_api/services/daemon_manager.py` | Import `resolve_runs_dir`, `resolve_logs_dir`, `resolve_worktrees_dir` from sibling `runtime_resolver`; route `_pid_path`, `_log_path`, `_current_ticket`, and `--worktrees-dir` through the resolver; add `log.parent.mkdir()` before opening the log file; add `sync_main()` function |
| `services/control_api/routes/daemon.py` | Add `POST /daemon/sync-main` endpoint |
| `apps/dashboard/src/api/daemon.js` | Add `export const syncMain = () => client.post('/daemon/sync-main')` |
| `apps/dashboard/src/pages/DaemonPage.jsx` | Add `<ActionButton label="Sync Main" action={daemonApi.syncMain} variant="secondary" onSuccess={fetchStatus} />` alongside the existing daemon control buttons |

All acceptance criteria from the plan are met: the daemon now reads/writes its PID and log through `AI_DEV_FACTORY_RUNTIME_ROOT` when set, starts with the correct `--worktrees-dir`, auto-creates the logs dir, and the dashboard exposes a functional Sync Main button.
