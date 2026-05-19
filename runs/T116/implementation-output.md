All changes are in scope. Here's a summary of what was implemented across the 8 plan steps:

---

**Files modified:**

| File | Change |
|------|--------|
| `services/control_api/services/board_service.py` | Step 1: `_load_runtime_db` now reads DB from `RUNTIME_ROOT/.runtime/` when env var is set. Step 5: `get_board` computes `state_dir` and uses it for JSON fallback of workers/issue-index. |
| `tools/agent_runner/runtime_db.py` | Step 2: Removed `subprocess` import and the `git rev-parse --git-common-dir` call. Dev fallback now uses `Path(__file__).resolve().parent.parent.parent` (stable, CWD-independent). |
| `tools/agent_runner/run_daemon.py` | Step 3: `state_dir` threaded through `launch_ticket`, `run_once`, `poll_github_issues`; workers.json and .issue-intake.json now read/written from `state_dir`. Step 4: `_LOG_FILE` module variable + `_log()` writes to `RUNTIME_ROOT/logs/daemon.log` when set. |
| `services/control_api/services/runtime_resolver.py` | Step 6: Added `resolve_state_dir()` and `resolve_logs_dir()`. |
| `deploy/bootstrap.sh` | Step 7: Best-effort migration of SQLite DB, `workers.json`, and `.issue-intake.json` from old locations to canonical ones. Never overwrites existing files. |
| `docs/ai/runtime-layout.md` | Step 8: Updated "état réel" section to reflect T116 changes and residual gaps. |
| `docs/ai/decisions-log.md` | Step 8: New T116 entry documenting the structural decisions. |

**Key invariant preserved:** all changes fall back gracefully when `AI_DEV_FACTORY_RUNTIME_ROOT` is not set — dev-without-Docker keeps working as before.
