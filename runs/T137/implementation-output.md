Both fixes are in place and correct.

---

## Changes made

**Fix 1 — `run_sandbox.py:516`** — Added `"project_root": str(project_root)` to `state_base`. This ensures the cleanup endpoint can read the project root from `state.json` and call `git worktree remove --force`, preventing phantom entries in `.git/worktrees/`.

**Fix 2 — `sandbox.py:330`** — Added `re.fullmatch(r"[a-zA-Z0-9_\-]+", sandbox_id)` guard at the top of `cleanup_sandbox_run`, plus `import re`. A path-traversal attempt like `DELETE /sandbox-runs/..` now returns HTTP 400 before any filesystem path is constructed.

Two files modified, no architecture changes, no scope expansion.
