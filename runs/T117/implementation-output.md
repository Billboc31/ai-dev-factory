All fixes look correct. Here's a summary of what was changed to address the two blocking issues:

---

## Changes made

**BLOCKING #1 — Out-of-scope docker-compose.yml + deploy/.env**

- **`docker-compose.yml`**: Reverted volume mount back to `~/runtime/ai-dev-factory:/runtime` (host bind mount, as on `main`). Changed `env_file` from the single-string form to the long-form with `required: false` — `docker-compose up` now works on a fresh deploy even without a `.env` file. Removed the orphaned `volumes: runtime-data:` named-volume declaration.
- **`deploy/env.example` → `deploy/.env.example`**: Renamed to the conventional dotfile template name so users know to `cp deploy/.env.example deploy/.env` before first run.

**BLOCKING #2 — Rebase left in mid-conflict state**

- **`tools/agent_runner/run_daemon.py:_sync_ticket_branch()`**: Added `subprocess.run(["git", "rebase", "--abort"], ...)` in the failure path before returning `False`, so the worktree is never left stuck mid-rebase.

**Minor — unchecked `git checkout -f main`**

- **`tools/agent_runner/worktree_manager.py:ensure_intake_worktree()`**: Captured the return value of `git checkout -f main` and prints a stderr warning on non-zero exit. Added `import sys` at the top of the file.
