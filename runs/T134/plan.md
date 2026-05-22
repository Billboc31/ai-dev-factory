The plan is written. Here it is:

---

## Objective

Add a "Deploy & Test in Sandbox" action to the Deployer page that automatically creates an isolated git worktree and runtime sandbox, executes the project's operational scripts (`bootstrap.sh → build.sh → start.sh → healthcheck.sh`) in sequence inside the worktree, captures logs and exit codes per step, and reports the outcome (success or failure) in the dashboard — without touching the main runtime environment.

## Included

**`services/control_api/services/sandbox_runner.py`** *(new)*
- Sandbox ID generation: `{project_id}-{timestamp}`
- `create_sandbox` runs `git worktree add {path} HEAD`, creates isolated state/log dirs, writes initial `pending` state and a "latest pointer" file per project
- `_run_scripts` executes the four scripts in order inside the worktree (`cwd=worktree_path`), captures stdout/stderr/exit code/timestamps per step; stops and sets `failed` on any non-zero exit
- `start_sandbox_validation` acquires the per-project lock (same pattern as `deployer_runner`), spawns a daemon thread, returns immediately
- `get_sandbox_state` / `get_sandbox_logs` read from the latest sandbox's isolated files

**Hypothesis**: scripts exist at the worktree root. Coder must verify vs. `ops/` or similar.

**`services/control_api/models/schemas.py`** — add `SandboxStepResult`, `SandboxState`, `SandboxStatus`

**`services/control_api/routes/sandbox.py`** *(new)* — `POST /sandbox/start`, `GET /sandbox/status`, `GET /sandbox/logs`

**`services/control_api/main.py`** — register sandbox router

**`apps/dashboard/src/api/deployer.js`** — add `startSandboxValidation`, `getSandboxStatus`, `getSandboxLogs`

**`apps/dashboard/src/pages/DeployerPage.jsx`** — `SandboxStatusPanel` (state badge, per-step results), `SandboxLogsPanel` (collapsible, polls while running), "Deploy & Test in Sandbox" button

**`tests/test_sandbox_runner.py`** *(new)* — 6 test cases: worktree creation, full success, healthcheck failure, mid-pipeline failure, log capture, lock contention

## Excluded

AI fix loops, automatic script patching, commit/push after failure, retry loops, sandbox cleanup, remote deployment, tester-agent, parallel sandboxes.

## Acceptance criteria

- Button visible when `profile_present`; `POST /sandbox/start` returns immediately
- State transitions `pending → running → success/failed` visible via polling
- Failed script sets `failed` + `last_step`; subsequent scripts not executed
- Sandbox state/logs isolated from main `deploy-state.json` / `deploy.log`
- Git worktree is separate from the working tree
- Dashboard panels display state, step results, and logs
- All 6 tests pass
