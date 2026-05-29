All 51 tests pass. Here's a summary of what was implemented:

---

**Files modified:**

1. **`services/control_api/models/sandbox.py`** — Added `requested_ref`, `resolved_ref`, `commit_sha` optional fields to `SandboxState`.

2. **`services/control_api/services/sandbox_manager.py`** — Rewrote the branch path in `create_with_worktree()`:
   - Runs `git fetch origin <branch>` first; fails loudly with `RuntimeError` (and destroys the sandbox) if non-zero.
   - Runs `git rev-parse origin/<branch>` to get the exact remote SHA.
   - Replaces `git worktree add <path> <branch>` with `git worktree add --detach <path> <sha>` — guarantees the fetched commit, not a stale local ref.
   - Persists `requested_ref`, `resolved_ref`, `commit_sha` in sandbox state.

3. **`services/control_api/routes/deployer.py`** — Added `DeployRequest` (Pydantic model with `branch: str | None`), threaded `request: Request` into `trigger_deploy`, and routed branch deploys through `deployer_runner.run_deploy_sandboxed` with the shared `SandboxManager` from app state.

4. **`tests/test_sandbox_worktree.py`** — Updated `test_create_with_worktree_uses_branch_when_given` to expect `--detach <sha>` (not the bare branch name), and added five new tests: `fetches_before_checkout`, `uses_remote_sha_not_branch_name`, `fails_loudly_if_fetch_fails`, `records_ref_identity_in_state`.
