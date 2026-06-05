# Test Report — T177

## Summary

All 5 acceptance criteria **PASS**. No regressions introduced by this ticket.

---

## Acceptance Criteria

### AC1 — Request payload contains the selected runtime root

**PASS**

`EnvironmentProvisionRequest` (`services/supervisor/main.py:1260`) now declares `runtime_root: str | None = None`. Pydantic no longer silently drops the field when the control API forwards it via `body.model_dump(mode="json")`.

Verified by `test_provision_runtime_root_override_propagates`: POST with `runtime_root` returns HTTP 200 and `state.runtime_root` equals the submitted value.

### AC2 — Backend persists the value

**PASS**

`provision_environment_from_body` (`services/control_api/services/environment_provision.py:319`) reads `runtime_root` from the body dict and sets it on the `SandboxState` instance. The test captures `state.runtime_root` inside the mocked `deploy_operational_runtime` call and asserts it equals the submitted path.

### AC3 — Deploy reads the persisted value

**PASS**

`_resolve_runtime_root` (`services/control_api/services/sandbox_runtime_deploy.py:295`) reads `state.runtime_root` from the persisted state. When non-null, it derives the effective sandbox dir from the override path, validates it, creates the directory, and returns `"override"` as source. The test confirms the captured `state.runtime_root` inside the deploy call matches the submitted value.

### AC4 — Logs clearly show auto vs override mode

**PASS**

`deploy_operational_runtime` writes `runtime_root_source=auto` or `runtime_root_source=override` to both the sandbox log file (line 393–395) and `logger.info` (line 399–401). This was pre-existing behaviour for the auto case; the override path now reaches `_resolve_runtime_root` and returns `"override"` instead of the call never happening.

### AC5 — Invalid runtime root values fail validation (400)

**PASS**

`environments_provision` (`services/supervisor/main.py:1283–1289`) validates `runtime_root` before calling any provision logic: returns HTTP 400 for relative paths and paths containing `..`.

Verified by `test_provision_invalid_runtime_root_returns_400`: both `"relative/path"` and `"/a/../b"` return HTTP 400 with `"runtime_root"` in the error message.

---

## Test Execution

```
tests/test_environment_supervisor.py::test_provision_runtime_root_override_propagates  PASSED
tests/test_environment_supervisor.py::test_provision_invalid_runtime_root_returns_400  PASSED
tests/test_environment_supervisor.py::test_provision_endpoint_triggers_infra_bootstrap PASSED
tests/test_environment_supervisor.py::test_supervisor_provision_missing_host_project_root PASSED
```

### Pre-existing failure (not introduced by T177)

`tests/test_environment_supervisor.py::test_supervisor_provision_maps_and_validates_host_project_root` — fails on `main` with the same error (`422` instead of `200`), unrelated to the runtime root changes.

Confirmed by running the test against the main branch (after git stash): identical failure, identical error message.

---

## Regressions

None. The 62 suite-wide failures visible in the full `pytest tests/` run are all pre-existing on `main` (unrelated test files: `test_control_api_*`, `test_daemon_*`, `test_sandbox_worktree.py`, `test_ticket_timeline.py`). None of the files modified by T177 (`services/supervisor/main.py`, `tests/test_environment_supervisor.py`) introduced new failures.

---

## Validation: full propagation chain

| Layer | File | Status |
|---|---|---|
| Supervisor request model | `services/supervisor/main.py:1260` | Fixed — `runtime_root` field added |
| Supervisor input validation | `services/supervisor/main.py:1283–1289` | Added — 400 on invalid path |
| Provision service | `services/control_api/services/environment_provision.py:319` | Pre-existing — reads from body dict |
| SandboxState persistence | `services/control_api/models/sandbox.py:90` | Pre-existing — field exists |
| Deploy runtime resolution | `services/control_api/services/sandbox_runtime_deploy.py:295–317` | Pre-existing — override/auto logic |
| Deploy logging | `services/control_api/services/sandbox_runtime_deploy.py:393–401` | Pre-existing — logs runtime_root_source |

Root cause was exclusively the missing `runtime_root` field in `EnvironmentProvisionRequest`.
