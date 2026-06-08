Now I have a clear picture of the codebase. Writing the implementation plan.

## Objective

Restore full lifecycle log visibility by adding a "Full Logs" tab and runtime diagnostics panel to the environment logs UI, while keeping the existing step summary intact. The backend must also expose all runtime path diagnostics in its log aggregation response.

## Included

**Backend — `services/control_api/services/sandbox_runtime_deploy.py`**
- Extend `format_environment_logs()` (currently lines 100–153) to prepend a structured `[RUNTIME DIAGNOSTICS]` block including: `runtime_root`, `sandbox_root`, `source_path`, `project_root`, resolved script path, `runtime_root_source`, proxy diagnostics, and healthcheck detail lines from `validation.json`.
- Ensure the full `run.log` content is returned without truncation in this response.

**Backend — `services/control_api/routes/runtime_dashboard.py`**
- Add `runtime_root`, `sandbox_root`, `source_path`, `project_root`, `runtime_root_source` fields to the `SandboxRunSummary` response model so the UI can render a diagnostics panel from the existing list endpoint without a separate call.

**Frontend — `apps/dashboard/src/pages/DeployerPage.jsx`**
- In `SandboxStatusPanel`, add a "Full Logs" tab/button alongside the step summary that opens the existing `LogViewerDrawer` (currently wired on `RuntimeDashboardPage.jsx`), or renders an inline collapsible log panel from `run.log`.

**Frontend — `apps/dashboard/src/components/EnvironmentCard.jsx`**
- In the `LogsModal`, replace the single content area with two tabs: "Summary" (existing step list and `lifecycle_error`) and "Full Logs" (raw log content from `getEnvironmentLogs()`).
- Add "Copy logs" and "Download logs" buttons to the Full Logs tab.
- Expand the existing runtime paths section to also display `runtime_root_source`, proxy diagnostics, and healthcheck detail lines.

**Frontend — `apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx`**
- Change the "View logs" link on the `failing_step` banner to open the full logs view (the LogViewerDrawer or a modal), not just a scroll anchor.

**Frontend — API client**
- No new endpoints needed; `getSandboxLogs(id, offset)` already streams `run.log`. `getEnvironmentLogs(id)` will receive the extended diagnostics block once the backend is updated.

## Excluded

- Changing how `run.log` is written during deployment (the log file already contains the full lifecycle output).
- Modifying the supervisor, deploy pipeline, or healthcheck scripts.
- Adding authentication or per-user log access controls.
- Pagination or search inside the raw log viewer.
- Changes to the smoke test pipeline or validation logic.
- Any UI redesign of the step summary itself.

## Acceptance criteria

- The step summary (bootstrap / build / start / healthcheck with ✓/✗ status) is still visible and unchanged.
- A "Full Logs" tab or button is present on both the `DeployerPage` step panel and the `EnvironmentCard` log modal.
- The full logs view renders the complete `run.log` without truncation.
- The logs view includes a labeled `[RUNTIME DIAGNOSTICS]` block containing `runtime_root`, `sandbox_root`, `source_path`, `project_root`, resolved script path, `runtime_root_source`, proxy diagnostics, and healthcheck details.
- "Copy logs" copies the full raw text to the clipboard.
- "Download logs" triggers a file download of `run.log` content as a `.log` file.
- A healthcheck failure shows the detailed output (exit code, stdout/stderr lines from validation.json) in the diagnostics block.
- The `SandboxRunSummary` API response includes `runtime_root`, `sandbox_root`, `source_path`, `project_root`, and `runtime_root_source` fields.
- Existing runtime dashboard behavior (real-time log polling, health panel, proposal runs) is unaffected.
