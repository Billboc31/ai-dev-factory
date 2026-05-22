All 6 new tests pass and 11 existing deployer tests have no regressions. Here's the summary of changes:

## Files created or modified

| File | Change |
|---|---|
| `services/control_api/models/schemas.py` | Added `SandboxStepResult`, `SandboxState`, `SandboxStatus`, `SandboxLogsResponse` |
| `services/control_api/services/sandbox_runner.py` | **New** — lock, state/log management, worktree creation, script execution |
| `services/control_api/routes/sandbox.py` | **New** — `POST /sandbox/start` (202), `GET /sandbox/status`, `GET /sandbox/logs` |
| `services/control_api/main.py` | Imports and registers `sandbox.project_router` |
| `apps/dashboard/src/api/deployer.js` | Added `startSandboxValidation`, `getSandboxStatus`, `getSandboxLogs` |
| `apps/dashboard/src/pages/DeployerPage.jsx` | Added `SandboxStatusPanel`, `SandboxLogsPanel`, "Deploy & Test in Sandbox" button, sandbox state polling |
| `tests/test_sandbox_runner.py` | **New** — 6 tests: worktree creation, full success, healthcheck failure, mid-pipeline failure, log capture, lock contention |

## Key design decisions

- **Async by design**: `POST /sandbox/start` returns 202 immediately; the sandbox runs in a daemon thread and releases the per-project lock on completion.
- **Per-sandbox isolation**: each run gets a unique `{project_id}-{timestamp}` ID and its own directory containing `state.json`, `run.log`, and the git `worktree/`.
- **Script skipping**: scripts not found in the worktree root are skipped gracefully (status `skipped`), so partial script sets work.
- **Lock pattern**: identical to `deployer_runner` — non-blocking acquire returns 409 when a sandbox is already running.
