75/75 pass. Implementation complete.

---

**Summary of all changes:**

**`services/control_api/services/sandbox_manager.py`** — core fix
- Added `_env_file_path(id)` and `_runtime_root_path(id)` helpers that derive paths from `self.sandboxes_dir` (the runtime resolver's source of truth)
- All path usages in `_run_compose`, `logs`, `stop`, `_start_sandbox_supervisor`, `_terminate_sandbox_supervisor`, `destroy`, and `create` now go through these helpers instead of reading stored `state.env_file` / `state.sandbox_runtime_root`
- `_read_state` uses `try/except FileNotFoundError` instead of `.exists()` check

**`services/control_api/services/infra_service_manager.py`** — structural check
- Replaced `"sandboxes" not in p.parts` with `not p.is_relative_to(get_sandbox_root())` — correctly handles any `SANDBOX_ROOT` value, not just paths containing the literal word "sandboxes"

**`services/control_api/models/sandbox.py`** — backwards compat
- `env_file: str = ""` — optional with default; marked informational since paths are now reconstructed dynamically

**Tests** — updated two existing tests to set `SANDBOX_ROOT` (required by the new structural check), added 6 new tests covering path helpers, stale-state resilience, custom sandbox root, missing sandbox 404, and no-hardcoded-paths assertion.
