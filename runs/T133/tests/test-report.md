The pre-existing test failures (46 total) were introduced by earlier tickets (T100, T028, T026) — predating T133. The sandbox tests (23) are all new in T133's commit and all pass.

Now I have everything I need. Let me write the test report.

---

## Test Report — T133: Isolated Sandbox Deployment Runtime

### Summary

**Result: PASS**

All 23 sandbox tests pass. No regressions introduced by T133.

---

### Acceptance Criteria

| Criterion | Status | Evidence |
|---|---|---|
| Deployer can create an isolated sandbox runtime | **PASS** | `POST /sandboxes` returns 201 with state (ticket_id, ports, compose_project, env_file). `test_create_sandbox_returns_201` passes. |
| Sandbox does not conflict with main runtime | **PASS** | Slot allocation starts at 1, so web port = 3000 + slot×100 ≥ 3100 and api port ≥ 8180. `test_create_does_not_conflict_with_main_runtime` explicitly asserts `ports["web"] != 3000` and `ports["api"] != 8080`. |
| Ports are isolated | **PASS** | Each sandbox gets a unique slot, guaranteeing distinct ports. Thread-safe `_registry_lock` prevents concurrent collisions. `test_create_allocates_unique_ports` verifies two sandboxes never share port values. Slot is released on destroy and reusable. |
| Logs/status are accessible | **PASS** | `GET /sandboxes/{id}` returns full state. `GET /sandboxes/{id}/logs` runs `docker compose logs` scoped to the sandbox project name. Both endpoints have passing tests. |
| Cleanup works correctly | **PASS** | `POST /sandboxes/cleanup?max_age_days=N` destroys sandboxes older than N days. Age-based cutoff uses timezone-aware datetimes. `test_cleanup_old_removes_stale_sandboxes` backdates a sandbox 10 days and confirms destruction. `test_cleanup_old_keeps_recent_sandboxes` confirms fresh sandboxes survive. |
| Existing runtime remains unaffected | **PASS** | Sandbox code is fully additive — new module, new route, new model. `main.py` gets one import and one `include_router` call, nothing else changed. `bootstrap.sh` adds only a `mkdir` for the sandboxes directory. 610 pre-existing passing tests continue to pass. |

---

### Additional Verifications

**Docker Compose project name isolation**: Each sandbox sets `COMPOSE_PROJECT_NAME=sandbox-{id}` and passes `-p sandbox-{id}` to every compose command, giving fully namespaced containers, volumes, and networks.

**State persistence**: State is written to `sandboxes/{id}/state.json` as JSON; the port registry is at `sandboxes/port-registry.json`. Both survive process restarts.

**Dashboard visibility**: `SandboxPanel.jsx` is registered at `/sandboxes` in the React router with a sidebar nav link. It polls every 5 seconds, shows status badges, ports, and a logs modal.

**Lifecycle transitions verified**: `stopped → running → stopped → error` all tested.

**Error handling**: Unknown sandbox ID returns 404. Start failure sets status to `error` without crashing the service.

---

### Pre-existing Failures (not introduced by T133)

46 tests in `test_ticket_timeline.py`, `test_daemon_checkpoint.py`, `test_control_api_subprocess.py`, `test_daemon_issue_polling.py`, and `test_run_daemon.py` fail on this branch. Git history confirms all were introduced by tickets T026, T028, and T100, prior to T133. They are not regressions from this ticket.

---

### Conclusion

The T133 implementation fully satisfies all acceptance criteria. The sandbox runtime is properly isolated from the main runtime by ports, Docker Compose project names, and filesystem paths. All 23 new tests pass cleanly.
