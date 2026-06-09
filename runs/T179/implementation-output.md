All 5 source files changed as intended. Here's a summary of what was implemented:

---

**Backend — `runtime_dashboard.py`**
- Added `sandbox_root`, `source_path`, `project_root`, `runtime_root_source` fields to `SandboxRunSummary`
- `_parse_sandbox_state` now populates them from `state.json` (uses `"override"/"auto"` logic for `runtime_root_source`)

**Backend — `sandbox_runtime_deploy.py`**
- `format_environment_logs()` now prepends a `=== RUNTIME DIAGNOSTICS ===` block as the first section, exposing: `project_root`, `sandbox_root`, `runtime_root`, `runtime_root_source`, `source_path`, `healthcheck_status`, `smoke_status`, `failing_step`, and proxy backend diagnostics from `validation.json`

**Frontend — `EnvironmentCard.jsx`**
- `LogsModal` split into two tabs: **Summary** (lifecycle step list with ✓/✗ icons and error block) and **Full Logs** (raw log text)
- Full Logs tab has **Copy logs** and **Download logs** buttons
- Runtime paths section now also shows `runtime_root_source` (derived as `override` or `auto`)

**Frontend — `LogViewerDrawer.jsx`**
- Added **Copy** and **Download** buttons to the drawer header (appear only when log content is available)

**Frontend — `SandboxRunsTable.jsx`**
- Info row now displays `runtime_root_source`, `sandbox_root`, `source_path`, and `project_root` when present
