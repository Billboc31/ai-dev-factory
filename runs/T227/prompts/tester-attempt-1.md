# T227 — Tester Report

**Date**: 2026-08-02  
**Branch**: `ticket/T227-add-pull-and-local-backend-frontend-redeployment-a`

---

## Test execution summary

| Suite | Tests | Result |
|---|---|---|
| `tests/supervisor/test_workspace_redeploy.py` | 34 | ✅ All passed |
| `tests/control_api/test_workspace_redeploy_proxy.py` | 4 | ✅ All passed |
| `apps/dashboard/tests/ProjectWorkspacePanel.test.jsx` | 8 | ✅ All passed |
| `tests/supervisor/test_supervisor.py` (pre-existing) | 1 FAIL | ⚠ Pre-existing, unrelated to T227 |

**Total T227 tests: 46 passed, 0 failed.**

Pre-existing failure `test_lifespan_restores_exec_cmd_and_restart_policy` reproduces on main with no T227 changes applied (confirmed via `git stash`). Not a regression.

---

## Acceptance criteria

### AC1 — "pull and redeploy this project" resolves to the active workspace project
**PASS** — `workspace_chat()` is scoped to `project_id` from the URL path; the AI system prompt includes `project_id:` context. The LLM cannot target a different project than the active one.

### AC2 — Backend only, frontend only, or both
**PASS** — `components` is validated against `project_block["redeploy"].keys()` at proposal time and at execution time. `test_job_backend_only` and `test_job_frontend_only` verify each subset.

### AC3 — No mutation or restart before confirmation
**PASS** — The background job is spawned only inside `workspace_action_confirm()` after the `action_id` is validated. No subprocess is launched during the chat phase.

### AC4 — Supervisor executes only the configured recipe
**PASS** — `_run_redeploy_job()` reloads YAML config at execution time and re-derives `repo_path`, `default_branch`, and `service` from it. LLM-supplied values are ignored. `test_job_stale_service_name_ignored` and `test_job_config_reloaded_at_execution` confirm this.

### AC5 — Branch pulled using configured safe strategy
**PASS** — Uses `git pull --ff-only origin <default_branch>`, where `default_branch` is loaded from YAML, never from the LLM. A branch mismatch aborts before pull (`test_job_branch_mismatch_rejected`).

### AC6 — Services rebuilt/restarted per requested components
**PASS** — `docker compose up -d --build <service>` executed per component in order. First failure stops the loop.

### AC7 — Concurrent redeployment prevented
**PASS** — Per-project `threading.Lock` acquired non-blocking; returns HTTP 409 if held (`test_confirm_concurrent_returns_409`). Lock released unconditionally in `finally`.

### AC8 — Pull, build, restart, and health-check progress visible
**PARTIAL** — `PULLING` and `BUILDING_<component>` stages are set and polled by the frontend every 2 seconds. However, **no `VERIFYING` (health-check) stage is implemented** in the backend; the job transitions from `BUILDING_*` directly to `SUCCEEDED` with no service health probe. The `STAGE_LABELS` map on the frontend declares `VERIFYING: 'Verifying…'` but this code path is never reached. Health verification is absent from the execution flow.

### AC9 — Success returns deployed revision and preview URL
**PASS** — `deployed_sha` (from `git rev-parse --short HEAD`) and `preview_url` (from YAML) are included in the `SUCCEEDED` job record. The frontend renders `Deployed successfully (sha: <sha>) — <url>`.

### AC10 — Failure returns failed stage and log excerpts
**PASS** — `error_stage` and `error_excerpt` (first 500 chars of stderr) are set on failure. The frontend renders `${error_stage}: ${error_excerpt}`.

### AC11 — Arbitrary model/frontend-supplied commands rejected
**PASS** — All paths, branches, and service names are re-derived from YAML at execution time. LLM branch param is stripped at proposal time (`test_chat_branch_param_ignored`). No user-controlled values reach subprocess calls.

### AC12 — Existing workspace conversations unaffected
**PASS** — Redeploy changes are additive. Existing capabilities (`restart_daemon`, `rerun_dependency_analysis`, `resume_execution`), issue creation flow, and non-mutating chat all continue to work. No regressions observed.

---

## Issues found

### MINOR — Confirmation card omits "Local changes" row when clean

**Requirement**: The confirmation card must display *whether* local uncommitted changes were detected.

**Observed**: The row is only rendered when `has_dirty_warning === true`:

```jsx
{message.proposedAction.has_dirty_warning === true && (
  <tr>
    <td>Local changes</td>
    <td>⚠ Uncommitted changes detected</td>
  </tr>
)}
```

When `has_dirty_warning` is `false` (clean) or `null` (detection failed), the row is absent. The user cannot distinguish "clean repo" from "status check failed" from the confirmation card. The ticket requires showing this field in both states.

**Impact**: Non-blocking display gap. Safety enforcement (dirty check re-run at execution time) is unaffected.

### MINOR — VERIFYING / health-check stage not implemented

**Requirement**: "Stream or periodically return progress for pull, build, restart, and **health verification**." Suggested states include `VERIFYING`.

**Observed**: The backend job goes `PULLING → BUILDING_<component>... → SUCCEEDED` without any health probe. If a service starts but immediately crashes, the deployment is reported as `SUCCEEDED`.

**Impact**: Non-blocking, but a gap versus the health-verification requirement. Services are not verified as healthy post-restart.

### INFORMATIONAL — Audit trail is log-based only, no actor field

**Requirement**: "Record the request, confirmation, resolved action, executor result, and actor in the audit trail."

**Observed**: Events are written via `logger.info()` (e.g. `workspace: confirming capability=... project_id=... action_id=...`, `redeploy %s: stage=SUCCEEDED sha=...`). No structured audit record with an actor field exists; the workspace has no authentication layer.

**Impact**: Acceptable for a local single-user tool, but the "actor" requirement is unmet. Should be tracked as follow-up.

---

## Regressions

None. All previously passing tests continue to pass.

---

## Verdict

**VALIDATION PARTIAL — non-blocking issues only**

All core acceptance criteria are met: project resolution, component targeting, pre-confirmation safety gate, config-only execution, concurrent lock, progress polling, success/failure output, command-injection prevention, and regression safety.

Two minor gaps remain (confirmation card clean-state display, no health-check step) and one informational gap (audit actor). None are blocking.
