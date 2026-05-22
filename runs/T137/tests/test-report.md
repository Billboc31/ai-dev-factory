I have everything I need. Here is the test report.

---

## Test Report — T137: Sandbox Isolated Ports and UI Management

### Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC1 | Sandbox validation no longer conflicts with main ports | **PASS** | Port slot system: slot 0 reserved for main (8080/3000), sandboxes start at slot 1 (`api=8080+slot×100`, `web=3000+slot×100`). Direct test confirmed 3 concurrent sandboxes allocate 8180/8280/8380 — no collision. |
| AC2 | Every sandbox has its own env file | **PASS** | `_write_sandbox_env()` writes `deploy.env` in each `sandboxes/{sandbox_id}/` dir before the worktree is created. File contains `API_PORT`, `WEB_PORT`, `COMPOSE_PROJECT_NAME`, `SANDBOX_ID`, `AI_DEV_FACTORY_RUNTIME_ROOT`, `AI_DEV_FACTORY_PROJECT_ROOT`, `AI_DEV_FACTORY_SUPERVISOR_PORT`. Isolation test confirms env files are non-overlapping. |
| AC3 | Every sandbox uses a unique compose project name | **PASS** | `compose_project = f"sandbox-{sandbox_id}"` where `sandbox_id = f"{project_id}-{YYYYMMDDTHHMMSS}"`. Uniqueness enforced by timestamp. Confirmed by `test_concurrent_create_unique_compose_names`. |
| AC4 | Ports visible in UI and logs | **PASS** | `run_sandbox.py:523` logs `port_slot`, `api_port`, `web_port`. State JSON includes `"ports": {…}`. `SandboxRunsPanel.jsx:122–131` renders a Ports column for each row. `docker-compose.yml` uses `${API_PORT:-8080}` and `${WEB_PORT:-3000}`. |
| AC5 | Historical sandboxes visible in UI | **PASS** | `GET /sandbox-runs` scans all `sandboxes/*/state.json`. `SandboxRunsPanel` auto-refreshes every 10 s. Integration test confirmed: 2 historical runs returned with all fields (ID, project, state, timestamps, last step, ports, worktree path). |
| AC6 | Cleanup works safely | **PASS** | `DELETE /sandbox-runs/{id}` validates `sandbox_id` against `[a-zA-Z0-9_\-]+` (path traversal blocked). Two-phase worktree removal: `git worktree remove --force` → fallback `shutil.rmtree`. Port slot released. Then only the specific sandbox dir removed. Integration test confirmed the other sandbox is untouched after cleanup. |
| AC7 | Existing sandbox validation still works | **PASS** | All 90 sandbox tests pass. Three separate FastAPI routers mounted independently. New `SandboxValidationStatus` fields (`ports`, `worktree_path`, `compose_project`) are optional with defaults — fully backward compatible. |

### Regressions

None detected. All 90 sandbox-related tests pass. The full suite shows 46 pre-existing failures (unrelated to T137) including `test_lifespan_restores_exec_cmd_and_restart_policy`, confirmed pre-existing on the current branch before any T137 changes.

### Blocking Issues

None.

### Validation Limits

- UI rendering was not verified in a live browser (no running server). The component logic and API wiring are correct based on code review and API integration tests.
- Port allocation race-condition safety relies on `fcntl.LOCK_EX` — correct on Linux/macOS, but not tested under actual concurrent load (the unit tests use sequential allocation via `SandboxManager`).

### Verdict

**VALIDATION PASSED** — all 7 acceptance criteria satisfied.
