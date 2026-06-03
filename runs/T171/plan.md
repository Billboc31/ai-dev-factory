Now I have enough context to write the plan.

## Objective

Replace the existing `git worktree` + local-repo approach in the environment deploy flow with a fresh `git clone` of the selected repository and branch into a per-environment `source/` directory, so every deployment is deterministically built from the chosen branch and cannot be influenced by stale local checkouts.

## Included

- **`services/control_api/services/sandbox_manager.py`**
  - Remove `create_with_worktree()` (or rename/refactor it)
  - Add `create_with_fresh_clone(project_root, repo_url, branch, sandbox_dir)`:
    - creates `{sandbox_dir}/source/` and `{sandbox_dir}/runtime/` directories
    - runs `git clone --branch <branch> <repo_url> {sandbox_dir}/source/`
    - after clone, logs `pwd`, `git branch --show-current`, `git rev-parse --short HEAD`
    - asserts checked-out branch matches the requested branch; raises a hard error if not
  - Update `Sandbox` dataclass / namedtuple: replace `worktree_path` field with `source_path` pointing to `{sandbox_dir}/source/`

- **`services/control_api/services/deployer_runner.py`**
  - In `_do_deploy()` (line ~296): remove the `worktree_path`-vs-`project_root` dual-path; always use `sandbox.source_path` as `cwd`
  - Remove any fallback to `project_root` when no branch is specified — require `source_path` to always be set

- **`services/control_api/routes/deployer.py`**
  - In `trigger_deploy()`: pass the repository URL (from environment config or project registry) to the new clone logic; ensure branch is always forwarded (make it a required field or default to `main` with an explicit log, never silently inherit the current shell branch)

- **`services/control_api/services/sandbox_runtime_deploy.py`** *(likely no change, but verify)*
  - Confirm that supervisor/Traefik setup already reads paths from `sandbox.source_path`; update any hardcoded worktree references if found

- **`services/control_api/dependencies.py`** *(or wherever `resolve_project` lives)*
  - Ensure the repository clone URL is resolvable from the project/environment config so it can be passed to the cloner

- **Tests** (existing test files covering deploy / sandbox creation):
  - Update fixtures/mocks to reflect `source_path` instead of `worktree_path`
  - Add a test asserting that a branch mismatch after clone aborts the deploy
  - Add a test asserting the deploy `cwd` is `{sandbox_dir}/source/`, never `project_root`

## Excluded

- Changes to the web UI or branch-selection interface
- Changes to `docker-compose.yml`, `deploy/bootstrap.sh`, or Traefik/supervisor configuration
- Caching or partial-clone optimisations (shallow clone is acceptable but not required)
- Handling of private repositories requiring SSH keys (assumed already handled by existing credential setup or out of scope)
- Cleaning up stale `{sandbox_dir}/source/` directories after deploy (lifecycle cleanup is a separate concern)
- Changes to the ticket/PR/memory workflow infrastructure

## Acceptance criteria

- Deploying an environment with branch `T170` selected clones the repository at the `T170` ref; the deploy logs show `git branch --show-current` output matching `T170` and a valid short SHA.
- If the cloned branch does not match the selected branch, the deploy exits with a non-zero status and a clear error message before any bootstrap/build/start scripts run.
- `deployer_runner.py` contains no reference to `project_root` as a fallback `cwd`; only `source_path` is used.
- Two concurrent deploys targeting different branches produce independent `source/` directories and do not interfere with each other.
- Existing local worktrees in `~/runtime/ai-dev-factory/worktrees/` have no effect on any deployment outcome.
- All existing unit/integration tests pass; new tests covering clone-path and branch-mismatch cases pass.
