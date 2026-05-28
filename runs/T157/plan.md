I have all the context I need. Here is the implementation plan:

---

## Objective

Add a mandatory `git fetch origin <branch>` step before sandbox worktree creation so the deployer always checks out the latest remote commit for a requested branch. Persist the deployed ref identity (requested ref, resolved ref, commit SHA) in sandbox state so the Runtime UI can display it.

## Included

### `services/control_api/models/sandbox.py` — `SandboxState`
- Add three optional fields:
  - `requested_ref: str | None = None` — the branch/ref as requested by the caller
  - `resolved_ref: str | None = None` — the full remote ref used (e.g. `origin/<branch>`)
  - `commit_sha: str | None = None` — the exact commit SHA checked out

### `services/control_api/services/sandbox_manager.py` — `create_with_worktree()`
- When `branch` is provided, insert three steps before `git worktree add`:
  1. `git fetch origin <branch>` (cwd=project_root) — fail loudly with a `RuntimeError` (and destroy the sandbox) if the fetch returns non-zero or the branch does not exist remotely
  2. `git rev-parse origin/<branch>` — resolve the SHA of the fetched remote commit
  3. Replace `git worktree add {path} {branch}` with `git worktree add --detach <sha>` — guarantees the worktree points to the fetched remote commit, not a stale local ref
- Populate `requested_ref`, `resolved_ref`, `commit_sha` in the state returned and persisted
- Add log lines for: requested ref, remote ref being fetched, resolved SHA, worktree path

### `services/control_api/routes/deployer.py` — `trigger_deploy`
- Add a `DeployRequest` Pydantic body with `branch: str | None = None`
- If `branch` is provided: resolve `SandboxManager` from `request.app.state` (same lazy-init pattern used in `routes/sandbox.py` and `routes/environments.py`) and call `deployer_runner.run_deploy_sandboxed(project_id, project_root, sandbox_manager, branch=branch)`
- If no `branch`: keep the existing `deployer_runner.run_deploy(project_id, project_root)` call unchanged
- Also thread `Request` into the handler signature (already needed for app state access)

### `tests/test_sandbox_worktree.py` — new and updated tests
- **Update** `test_create_with_worktree_uses_branch_when_given`: after the change, `worktree add` will use `--detach <sha>` instead of the bare branch name; update the assertion to verify the SHA is used and `--detach` is present
- **Add** `test_create_with_worktree_fetches_before_checkout`: captures all subprocess calls in order; asserts `git fetch origin <branch>` appears before `git worktree add`
- **Add** `test_create_with_worktree_uses_remote_sha_not_branch_name`: asserts `worktree add` receives the SHA returned by `rev-parse`, not the branch string
- **Add** `test_create_with_worktree_fails_loudly_if_fetch_fails`: mocks fetch to return non-zero; asserts `RuntimeError` is raised with a message containing the branch name, and the sandbox is destroyed (list returns empty)
- **Add** `test_create_with_worktree_records_ref_identity_in_state`: verifies `state.requested_ref`, `state.resolved_ref`, `state.commit_sha` are populated for a branch deploy

### `tests/test_deployer_execution.py` — updated tests
- Existing tests that mock `subprocess.run` and exercise the sandboxed path must account for the additional `fetch` and `rev-parse` calls; update mock side-effects to return success for these calls

## Excluded

- No changes to `run_sandbox.py` `_create_worktree()` (validation-worker path, not the deployer path)
- No changes to `tools/agent_runner/worktree_manager.py` (ticket intake path)
- No changes to Traefik routing, port allocation, or smoke test semantics
- No automatic merge, rebase, or resolution of diverged branches
- No mutation of the main production clone working tree beyond a safe `git fetch`
- No changes to bootstrap/build/start/healthcheck script logic
- No persistent environment management changes

## Acceptance criteria

- When `POST /projects/{id}/deployer/deploy` is called with `{"branch": "ticket/T156-..."}`, `git fetch origin ticket/T156-...` executes before any `git worktree add`
- The sandbox worktree HEAD equals `git rev-parse origin/<branch>` at the moment of deployment
- A second deploy after a new commit is pushed fetches and uses the newer commit
- If the branch does not exist remotely, deployment fails with a `RuntimeError` whose message names the missing branch; no silent fallback to HEAD or main
- `SandboxState` stored in `state.json` includes non-null `requested_ref`, `resolved_ref`, and `commit_sha` for any branch deploy
- Deploying without a branch (no request body or `branch: null`) continues to call `run_deploy()` and is unaffected
- All existing tests in `test_sandbox_worktree.py` and `test_sandbox_manager.py` pass (with the one updated assertion noted above)
