Now I have enough context to write the plan.

## Objective

Replace the current worktree-based deploy source with a fresh `git clone` + branch checkout for every environment deploy, so that the code actually deployed always matches the branch selected in the environment UI.

## Included

- **`services/control_api/services/sandbox_manager.py`** — in the sandbox/worktree provisioning section (around lines 399–470): replace the `git fetch` + `git worktree add --detach` sequence with a `git clone <repo_url> source/` + `git checkout <branch>` sequence inside a new per-sandbox `source/` subdirectory. Remove the `git worktree remove` call from the destruction path (lines 603–607); replace with `shutil.rmtree` of the `source/` directory.

- **`services/control_api/services/deployer_runner.py`** — in `_do_deploy()` (around lines 286–407): add a pre-build verification step that runs, in the checkout directory:
  ```bash
  pwd
  git branch --show-current
  git rev-parse --short HEAD
  ```
  and compares the checked-out branch to the requested branch. If they do not match, abort deployment with a clear error before any component is started.

- **`services/control_api/models/sandbox.py`** — update `SandboxState` (lines 51–89): replace the `worktree_path` field with `source_path` (pointing to `<sandbox_dir>/source/`) so that downstream code uses the correct fresh-clone directory.

- **All callers of `sandbox.worktree_path`** — grep and update to `sandbox.source_path`: at minimum `deployer_runner.py` (line 296, 585) and `run_sandbox.py`.

- **`services/control_api/services/deployer_runner.py`** — ensure `project_root` passed into `_do_deploy` is the new `source_path`, not the original `project_root`. Docker Compose commands and host-type component commands must run with `cwd=source_path`.

- **`services/control_api/services/undeploy_runner.py`** — update cleanup logic (lines 112–159) to remove `source/` directory instead of calling `git worktree remove`.

## Excluded

- Changing the port allocation, Docker Compose project naming, or Traefik routing.
- Changing the supervisor path-rewriting or `HOST_PROJECT_ROOT` volume mounts in docker-compose.yml.
- Any changes to the AI agent worktree flow in `tools/agent_runner/worktree_manager.py` — that is a separate concern.
- Support for "reuse existing clone if already present" caching — always fresh per the ticket requirement.
- CI or test environment changes beyond unit tests covering the new clone/verify logic.

## Acceptance criteria

- Deploying an environment with branch `T170` clones the repo fresh and checks out `T170`; deploy logs contain `git branch --show-current` output showing `T170` and the corresponding short SHA.
- Selecting branch `main` while a `T170` worktree exists locally does not cause `T170` code to be deployed.
- If `git clone` fails (bad URL, network error), deployment aborts immediately with a non-zero exit and a clear error in the deploy log.
- If the checked-out branch does not match the requested branch after checkout, deployment aborts before any component is started.
- Two simultaneous deployments for different branches produce independent `source/` directories and do not interfere with each other.
- After undeployment, the `source/` directory is removed (no stale clone left on disk).
