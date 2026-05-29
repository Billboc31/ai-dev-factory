Now I have a complete picture of the codebase. Here is the implementation plan.

---

## Objective

Fix all sandbox path construction in environment runtime actions to route exclusively through the runtime resolver instead of relying on absolute paths persisted in `SandboxState`. Remove the hardcoded `"sandboxes"` string check in `infra_service_manager.py` and add user-readable error handling for missing sandbox cases.

---

## Included

### `services/control_api/services/sandbox_manager.py`

- Add two private path helpers that reconstruct paths from the current `sandboxes_dir` (which is always sourced from `get_project_sandbox_dir()`):
  - `_env_file_path(sandbox_id: str) -> Path` → `self._sandbox_dir(sandbox_id) / ".env"`
  - `_runtime_root_path(sandbox_id: str) -> Path` → `self._sandbox_dir(sandbox_id) / "runtime"`
- Replace all usages of `state.env_file` in operations with `str(self._env_file_path(state.id))`:
  - `_run_compose`: `--env-file` argument
  - `logs`: `--env-file` argument
- Replace all usages of `Path(state.sandbox_runtime_root)` with `self._runtime_root_path(state.id)`:
  - `stop`: stale pid/lock cleanup loop
  - `_start_sandbox_supervisor`: runtime root directory creation and supervisor log path
  - `_terminate_sandbox_supervisor`: pid file lookup
  - `destroy`: `runtime_root` variable passed to `run_cleanup`
- In `create()`, use the same helpers to generate the values written to `.env` and stored in state (unifies the path generation source; `.env` content is unchanged).
- Wrap file operations in `_read_state` and `_run_compose` with `except FileNotFoundError` → raise `SandboxNotFoundError` with a readable message (`"sandbox not found: <id>"`), ensuring raw OS errors never reach the API.

### `services/control_api/services/infra_service_manager.py`

- In `resolve_host_runtime_root()`, replace the fragile string heuristic:
  ```python
  if "sandboxes" not in p.parts:
  ```
  with a structural check using the actual configured sandbox root:
  ```python
  from .runtime_resolver import get_sandbox_root
  if not p.is_relative_to(get_sandbox_root()):
  ```
  This correctly handles any `SANDBOX_ROOT` value, not only paths whose components spell out "sandboxes".

### `services/control_api/models/sandbox.py`

- Make `env_file` optional with a default: `env_file: str = ""`. The field is kept for backwards-compatibility with existing `state.json` files, but no operation uses the stored value for path resolution anymore. Add a brief comment marking the field as informational.

### `tests/test_environment_routes.py` — new test cases

- **Custom `SANDBOX_ROOT`**: set `SANDBOX_ROOT` to a `tmp_path` sub-directory and verify that create + redeploy + stop + delete + logs all succeed (paths are computed from the resolver, not the default `~/sandboxes`).
- **Missing sandbox returns readable 404**: call an action (`GET /environments/<id>`, `POST /environments/<id>/stop`) with a non-existent `id` and assert HTTP 404 with `"environment not found"` in the detail (not HTTP 500 or a raw stack trace).
- **No hardcoded `/sandboxes` path construction**: grep `sandbox_manager.py` for `Path("/sandboxes")` and `"/sandboxes/"` literals and assert zero matches.

### `tests/test_sandbox_manager.py` — new test cases

- **Path helpers use current `sandboxes_dir`**: instantiate `SandboxManager(sandboxes_dir=tmp_path / "custom")` and assert `_env_file_path` and `_runtime_root_path` return paths under that custom dir.
- **Operations ignore stale `env_file` in state**: write a `state.json` whose `env_file` field points to a wrong path; verify that `stop` and `logs` still resolve the correct path through the helper, not the stale stored value.

---

## Excluded

- Dashboard changes — `EnvironmentCard.jsx` already uses `env.id` (the UUID) for all action calls, not `env_name`.
- Configuration changes to `SANDBOX_ROOT`, `PROJECT_NAME`, or `HOST_RUNTIME_ROOT` env vars.
- Docker Compose or Traefik infrastructure changes.
- Worktree path handling (`worktree_path` field in `SandboxState`) — stored as absolute path but not involved in the reported failure.
- Full removal of `env_file` / `sandbox_runtime_root` from `SandboxState` (that is a separate migration requiring a schema version bump).

---

## Acceptance criteria

- `grep -r 'Path("/sandboxes")' services/` returns no results.
- `grep -r '"/sandboxes/"' services/` returns no results.
- `"sandboxes"` no longer appears as a string literal matched against path components in `infra_service_manager.py`.
- Environment actions (Redeploy, Stop, Refresh, Delete, View Logs) succeed when `SANDBOX_ROOT` is set to an arbitrary directory (covered by new test).
- Requesting an action on a non-existent sandbox returns HTTP 404 with `{"detail": "environment not found: <id>"}`, not HTTP 500 (covered by new test).
- All pre-existing tests in `test_environment_routes.py`, `test_sandbox_routes.py`, and `test_sandbox_manager.py` continue to pass.
