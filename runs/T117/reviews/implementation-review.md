IMPLEMENTATION_FIX_REQUIRED

---

**Review summary — T117**

The 6 planned fixes are all present and correctly implemented. Two blocking issues prevent approval:

**BLOCKING #1 — Out-of-scope changes to `docker-compose.yml` and `deploy/.env`**

The approved plan explicitly lists "Docker / deploy" as hors scope, yet both files were modified:
- `docker-compose.yml`: switches volume mount from `~/runtime/ai-dev-factory:/runtime` (host-accessible bind mount) to `runtime-data:/runtime` (Docker named volume). This potentially breaks host-side daemon access to runtime data — a T116 architecture regression.
- `deploy/.env`: deleted without a replacement template. `docker-compose.yml` still references `env_file: deploy/.env`, so `docker-compose up` fails with "no such file or directory" on any fresh deploy.

**Fix required**: either revert these changes (they're out of scope), or explicitly justify them, fix the broken `env_file` reference, and create a `deploy/.env.example` with the expected variables (no secrets).

**BLOCKING #2 — `git pull --rebase` without `git rebase --abort` on failure**

In `run_daemon.py:_sync_ticket_branch()`, when a rebase conflict occurs the function returns `False` but never calls `git rebase --abort`. The worktree is left in mid-rebase state. Every subsequent daemon cycle fails with "rebase in progress" — the ticket is permanently stuck.

**Fix required**: add `subprocess.run(["git", "rebase", "--abort"], cwd=cwd, capture_output=True)` in the failure path before logging and returning `False`.

Minor: `git checkout -f main` result is unchecked in `worktree_manager.py` — recommend logging a warning on non-zero return.

Also flagging pre-existing security issue: the deleted `deploy/.env` contained a real GitHub PAT that remains in git history — it should be revoked.
