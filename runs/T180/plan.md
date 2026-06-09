The plan is written to `runs/T180/prompts/planner-attempt-1.md`. Here it is:

---

## Objective

When `failing_step` is `healthcheck.sh`, the logs drawer must surface structured probe diagnostics (tested URLs, HTTP codes, curl results, Traefik/backend/network data) in a dedicated "Failure details" section above the raw full logs, without removing that raw view.

## Included

**`tools/agent_runner/run_sandbox.py`**
- Add `_parse_healthcheck_output(stdout, stderr, exit_code) -> dict` that parses healthcheck.sh stdout into `{ probes: [{name, url, result, http_code, note}], passed, failed, exit_code, raw_stderr }` using the well-defined stdout patterns.
- Call it for every healthcheck.sh step execution and pass the result to `_write_validation_json()` via a new `healthcheck_diagnostics` parameter.

**`services/control_api/routes/runtime_dashboard.py`**
- Add `DiagnosticsResponse` Pydantic model with `healthcheck_diagnostics: dict | None` and `backend_diagnostics: dict | None`.
- Add `GET /sandbox-runs/{sandbox_id}/diagnostics` endpoint reading both fields from `validation.json`.

**`apps/dashboard/src/api/runtimeDashboard.js`**
- Add `getSandboxDiagnostics(sandboxId)` API client function.

**`apps/dashboard/src/components/runtime-dashboard/LogViewerDrawer.jsx`**
- Accept `failingStep` prop; when `"healthcheck.sh"`, fetch diagnostics on mount and render a "Failure details" section (probe table + backend_diagnostics fields) above the raw logs.

**`apps/dashboard/src/pages/RuntimeDashboardPage.jsx`**
- Pass `failingStep={run?.failing_step}` to `<LogViewerDrawer>`.

## Excluded

- Modifying healthcheck.sh to write a sidecar file (stdout parsing in run_sandbox.py is sufficient).
- Changes to smoke.sh, auto-fix flow, or any other lifecycle step.
- Adding healthcheck_diagnostics to `SandboxRunSummary` or `/overview`.
- Backend diagnostics *collection* logic (already exists; only exposure is in scope).

## Acceptance criteria

- `validation.json` for a healthcheck failure includes `healthcheck_diagnostics` with a `probes` array, counts, and exit code.
- `GET /api/runtime-dashboard/sandbox-runs/{id}/diagnostics` returns both diagnostic fields (nullable), 200 for existing sandboxes, 404 for unknown.
- Opening the log drawer for a `failing_step = "healthcheck.sh"` run shows "Failure details" above raw logs with per-probe URL, HTTP code, and pass/fail badge.
- Drawer with any other `failing_step` (or none) shows no diagnostics section.
- Raw full log section and polling behavior are unchanged.
