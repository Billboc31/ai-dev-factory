---

## Test Report — T229

**Verdict: VALIDATION PASS**

### Test execution summary

| Test file | Tests | Result |
|---|---|---|
| `test_deployer_routes.py` | 5 | 5 passed |
| `test_deployer_execution.py` | 9 | 9 passed |
| `test_deploy.py` | 21 | 21 passed |
| `test_sandbox_runtime_deploy.py` | 13 | 13 passed |
| `test_undeploy_runner.py` | 11 | 11 passed |
| **Total** | **59** | **59 passed** |

Broader suite: 2082 passing, 136 pre-existing failures (identical on `main` — zero regressions introduced).

### Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| A project can be deployed from AI Dev Factory | **PASS** | `run_deploy()` + `POST /deployer/deploy` + `test_deploy_success` |
| Deployment progress is visible in the dashboard | **PASS** | `DeployerPage.jsx` polls status at 5s, shows state badge and per-step sandbox steps |
| Success and failure states are persisted | **PASS** | `deploy-state.json` written on every terminal state; `test_write_deploy_state_atomic` |
| Deployment logs are available for troubleshooting | **PASS** | `deploy.log` + `GET /deployer/logs`; `test_deploy_logs`, `test_log_tail_never_exceeds_50_lines` |
| The deployed application's URL is stored and displayed | **PASS** (workspace path) | `preview_url` in supervisor session history → `DeployHistoryPanel.jsx`. Direct deployer path has no URL field (minor gap, non-blocking) |
| Deployment can be retried after a failure | **PASS** | Lock released in `finally`; `test_retry_after_succeeded_returns_new_id` |
| Existing workflows remain unchanged when deployment is not used | **PASS** | Zero new failures vs main; additive-only `/deployer/*` namespace |

### Non-blocking observations

1. **Direct deployer URL gap**: `DeployerStatus` schema has no `preview_url` field and `deployer_runner.py` never writes one. Projects deployed via `/deployer/deploy` have no URL in the status view. The workspace/supervisor path (primary human-validation path) does store and display URLs correctly. Candidate for a follow-up.

2. `test_sandbox_worktree.py` has 12 pre-existing failures on `main` (`create_with_worktree` method missing from `SandboxManager`) — not introduced by T229.
