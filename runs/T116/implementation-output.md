All three fixes are in place. Here's a summary of what was changed:

**Fix 1 — Dead code (`runtime_resolver.py` helpers unused)**

`board_service.py`: Added `from .runtime_resolver import resolve_runs_dir, resolve_state_dir` and replaced the 7-line inline `runtime_root` block in `get_board()` with two resolver calls.

`run_daemon.py`: Added importlib loading of `runtime_resolver.py` at module level (same pattern as existing `runtime_db.py` load). In `main()`, replaced `state_dir = rt / "state"` / `state_dir = runs_dir` with `state_dir = _rr_resolve_state_dir(REPO_ROOT)`, and `_LOG_FILE = rt / "logs" / "daemon.log"` with `_LOG_FILE = _rr_resolve_logs_dir(REPO_ROOT) / "daemon.log"`.

**Fix 2 — `runtime_db.py` dev fallback creates DB in worktrees**

Restored `git rev-parse --git-common-dir` as the dev fallback. The git command is run with `cwd=Path(__file__).parent` — this works correctly even when the module is loaded from a worktree copy, because git always reports the main repo's `.git` as the common-dir regardless of which worktree you're in. Added `import subprocess`, resolved relative paths to absolute, and kept a last-resort module-location fallback. Updated the module docstring.

**Fix 3 — Missing invariant check**

Added `_log("WARNING: AI_DEV_FACTORY_RUNTIME_ROOT not set — using dev fallback paths")` in `main()` after the startup log lines, emitted whenever the daemon starts without a canonical runtime root configured.
