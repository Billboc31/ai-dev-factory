No new failures outside the pre-existing set. All failures are in files that were already failing on `main`.

---

## Test Report — T138 — Generic AI Sandbox Auto-Fix Loop

**Branch**: `ticket/T138-t138-generic-ai-sandbox-auto-fix-loop`  
**Date**: 2026-05-22  
**Tester**: Claude (Sonnet 4.6)

---

### Test Execution

**T138-specific tests**: 26/26 passed in 0.40s

| File | Tests | Result |
|---|---|---|
| `tests/test_auto_fix_proposer.py` | 13 | PASS |
| `tests/test_auto_fix_loop.py` | 10 | PASS |
| `tests/test_auto_fix_routes.py` | 3 | PASS |

**Regression check**: The full suite shows 44 failures. All 44 map to the same test files already failing on `main` (`test_control_api_artifacts.py`, `test_control_api_endpoints.py`, `test_control_api_subprocess.py`, `test_daemon_checkpoint.py`, `test_daemon_issue_polling.py`, `test_run_daemon.py`, `test_ticket_timeline.py`, `tests/supervisor/test_supervisor.py`). Zero new failures introduced by T138.

---

### Acceptance Criteria

**1. Sandbox failures can trigger a generic AI correction loop** — PASS  
`run_auto_fix_loop()` orchestrates the full collect → AI → validate → apply → rerun cycle. Entry point is `POST /projects/{project_id}/auto-fix/loop/start`. Validated by `test_loop_converges_after_one_fix`.

**2. The loop works without ai-dev-factory-specific assumptions** — PASS  
`collect_failure_context()` reads `deploy.yml`, sandbox state/logs, and operational scripts with no hardcoded service names, ports, or frameworks. Scripts discovered via `*.sh` glob (no hardcoded names). AI invoked via a generic `exec_cmd` subprocess — no provider SDK. Validated by `test_collect_reads_scripts_without_name_assumptions` and confirmed by source inspection of `auto_fix_proposer.py`.

**3. Retries are bounded and observable** — PASS  
The loop uses `for attempt in range(1, max_retries + 1)` — there is no unbounded while loop. `session["current_iteration"]` and `session["max_retries"]` are tracked and exposed through the API. The dashboard displays iteration count and max retries. Validated by `test_loop_fails_when_max_retries_reached`.

**4. Iteration history is persisted and visible** — PASS  
Each iteration is appended to `session["iterations"]` and written to disk at `{runtime_root}/auto-fix-sessions/{project_id}/{session_id}/state.json` after every iteration. Per-iteration logs written to `iter-{n}/run.log`. Validated by `test_loop_iteration_history_persisted`. Dashboard `IterationRow` exposes changed files, logs, and step details.

**5. Sandbox reruns after fixes** — PASS  
`run_auto_fix_loop()` calls `apply_patches()` then immediately calls `run_scripts_validation()` in the same iteration. The scripts run in-place from `project_root`, so patches are visible to the rerun. Validated by `test_loop_converges_after_one_fix`.

**6. Malformed AI output is safely rejected** — PASS  
`call_ai_runtime()` raises `ValueError` when the AI output contains no JSON array, and `RuntimeError` when the subprocess exits non-zero. Both are caught in the loop, the iteration is marked `"error"`, and the loop continues to the next attempt. Out-of-scope paths are rejected by `validate_patches()` (marked `valid=False` and skipped). If all patches are invalid the iteration is also marked `"error"`. Validated by `test_loop_handles_malformed_ai_output`, `test_call_ai_runtime_raises_on_malformed_output`, and all six `test_validate_patches_rejects_disallowed_paths` parameterized cases.

**7. The system never enters infinite retry loops** — PASS  
The loop is a bounded `for` over `range(1, max_retries + 1)`. No recursive calls, no unbounded `while`. Every error path sets a terminal iteration status and uses `continue` — not a retry restart. Validated by `test_loop_fails_when_max_retries_reached`.

**8. Successful fixes result in sandbox success state** — PASS  
When `run_scripts_validation()` returns `(True, None, steps)`, `session["status"]` is set to `"success"`, `session["finished_at"]` is recorded, and the loop returns immediately (no further iterations). Validated by `test_loop_converges_after_one_fix`.

**9. Failed retries result in clean terminal failed state** — PASS  
After exhausting `max_retries`, `session["status"] = "failed"` and `session["finished_at"]` is set before the function returns. The session on disk reflects the terminal state. Validated by `test_loop_fails_when_max_retries_reached`.

---

### Ticket-specified test cases

| Specified case | Test | Result |
|---|---|---|
| Successful convergence after fix | `test_loop_converges_after_one_fix` | PASS |
| Retry limit reached | `test_loop_fails_when_max_retries_reached` | PASS |
| Malformed AI output | `test_loop_handles_malformed_ai_output` | PASS |
| Patch application failure | `test_loop_handles_patch_application_failure` | PASS |
| Generic deploy.yml handling | `test_collect_reads_deploy_yml` | PASS |
| Iteration history persistence | `test_loop_iteration_history_persisted` | PASS |

---

### Observations (non-blocking)

- The `validate_patches()` function does not preserve the `reasoning` field from the AI output in its return value. This is not a bug — `run_auto_fix_loop()` captures reasoning from `raw_patches` before validation, so it is correctly stored in `iteration["reasoning"]`.
- There is no dedicated test for the loop path where all patches are out-of-scope (the `valid_patches` list is empty). The code path exists and is correct (`auto_fix_loop.py:248–252`), and it is indirectly covered by the path-validation tests. Not a blocker.
- The 44 pre-existing test failures are unrelated to T138. They existed on `main` before this branch was created.

---

### Verdict

**VALIDATION: PASS**

All 9 acceptance criteria satisfied. 26/26 tests pass. Zero regressions introduced.
