All good. Implementation is complete. Here's a summary of what was changed:

## Files Modified

**`services/control_api/services/runtime_resolver.py`**
Added `get_sandbox_root()`, `get_project_name()`, and `get_project_sandbox_dir()` — the single source of truth for sandbox path resolution. Reads `SANDBOX_ROOT` / `PROJECT_NAME` env vars with sensible fallbacks.

**`services/control_api/services/sandbox_manager.py`**
`__init__` now defaults to `get_project_sandbox_dir()` instead of `{RUNTIME_ROOT}/sandboxes`. Port registry moves with the sandbox dir.

**`tools/agent_runner/run_sandbox.py`**
Added `_sandbox_root()` and `_project_name()` helpers. `_sandbox_base_dir()` now resolves to `{SANDBOX_ROOT}/{PROJECT_NAME}/`. `sandbox_runtime_root` fixed to `sandbox_dir / "runtime"` (was incorrectly re-computing from runtime root). `_port_registry_paths()` uses the new sandbox dir. `SANDBOX_ROOT` and `PROJECT_NAME` propagated into `deploy.env` and `extra_env`.

**`services/control_api/routes/runtime_dashboard.py`**
Replaced `_sandboxes_root()` with `_get_sandboxes_dir()` (reads from the SandboxManager). Added `GET /runtime-dashboard/overview` returning `sandbox_root`, `project_name`, `project_sandbox_dir`, and sandbox list.

**`services/control_api/routes/sandbox.py`**
`_sandboxes_root()` now delegates to `get_project_sandbox_dir()`.

**`services/supervisor/main.py`**
Sandbox root logged in supervisor now reads `SANDBOX_ROOT`/`PROJECT_NAME` instead of `{RUNTIME_ROOT}/sandboxes`.

**`services/supervisor/path_mapper.py`**
Added `sandbox-root` mapping pair (`CONTAINER_SANDBOX_ROOT` → `HOST_SANDBOX_ROOT`).

**`docker-compose.yml`**
Added `${HOST_SANDBOX_ROOT:-~/sandboxes}:/sandboxes` bind-mount and `SANDBOX_ROOT=/sandboxes`, `CONTAINER_SANDBOX_ROOT=/sandboxes`, `PROJECT_NAME` env vars.

**`deploy/.env.example`**
Added `SANDBOX_ROOT`, `PROJECT_NAME`, `CONTAINER_SANDBOX_ROOT`, `HOST_SANDBOX_ROOT` variables with documentation.

**`apps/dashboard/src/api/runtimeDashboard.js`**
Added `getRuntimeOverview()`.

**`apps/dashboard/src/pages/RuntimeDashboardPage.jsx`**
Added `SandboxTopologyPanel` component and a "Sandbox Topology" section displaying sandbox root, project name, project sandbox dir, and sandbox count by status.
