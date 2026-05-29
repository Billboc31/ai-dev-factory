Now I have the full picture. The bug is in `environments.py:114-118`: when `start()` raises an exception, the route silently logs a warning and returns HTTP 201 with the pre-start (stopped) state — leaving a zombie sandbox directory in place. When `start()` returns with `status=error` (compose rc≠0), the same thing happens. The fix is surgical: destroy on failure, return 500.

## Objective

Fix `POST /environments` so that any `start()` failure — whether an exception or an `error` status from a failed compose run — destroys the partial sandbox and returns HTTP 500, instead of silently returning a stopped-but-unprovisioned environment that populates the UI with a fake card.

## Included

### `services/control_api/routes/environments.py` — `create_environment()`

- Replace the silent `except` block (lines 114–118) with a two-branch rollback:
  - If `mgr.start()` raises any exception: call `mgr.destroy(state.id)` (best-effort), then raise `HTTPException(status_code=500, detail="environment provisioning failed: <exc>")`.
  - If `mgr.start()` returns with `state.status == SandboxStatus.error`: call `mgr.destroy(state.id)` (best-effort), then raise `HTTPException(status_code=500, detail="environment provisioning failed: sandbox start returned error")`.
- Import `SandboxStatus` (already available via the existing models import) to check the returned status.
- Add validation that `body.project_root` resolves to an existing directory before calling `mgr.create()`; return HTTP 422 if not. This prevents wasting a port slot on an invalid path.

### `tests/test_environment_routes.py` — new test cases

- `test_create_environment_creates_sandbox_directory`: verify that after a successful POST `/environments`, `{sandboxes_dir}/{env_id}/state.json` and `{sandboxes_dir}/{env_id}/.env` both exist on disk.
- `test_failed_provisioning_returns_500_and_no_card`: patch `subprocess.run` to return `rc=1` for compose. Assert POST `/environments` returns HTTP 500. Assert `GET /environments` returns an empty list. Assert no sandbox directory remains under `sandboxes_dir`.
- `test_failed_provisioning_start_exception_no_card`: patch `SandboxManager.start` to raise a `RuntimeError`. Assert POST `/environments` returns HTTP 500. Assert no environment card survives in `GET /environments`.
- `test_create_environment_invalid_project_root`: POST with a `project_root` that does not exist on disk. Assert HTTP 422 before any sandbox directory is created.

## Excluded

- Changes to `SandboxManager.create()` or `SandboxManager.start()` internals — the rollback responsibility belongs to the route layer.
- Changes to the deploy flow, redeploy, stop, delete, or logs routes — they are not implicated.
- UI / frontend changes.
- Any refactor or restructuring of `SandboxManager`.
- Worktree creation during environment create (different flow, different ticket).
- Changes to the Docker Compose files or Traefik configuration.

## Acceptance criteria

- `POST /environments` with a non-existent `project_root` returns HTTP 422; no sandbox directory is created.
- `POST /environments` where `docker compose up -d` fails (rc≠0) returns HTTP 500; `GET /environments` lists 0 environments; no directory remains under `sandboxes_dir`.
- `POST /environments` where `SandboxManager.start()` raises an exception returns HTTP 500; same cleanup guarantees hold.
- `POST /environments` on a valid path succeeds (HTTP 201); `{sandboxes_dir}/{sandbox_id}/state.json` and `.env` exist after the call.
- All existing tests in `test_environment_routes.py` and `test_sandbox_manager.py` continue to pass.
- No code path in `create_environment()` returns HTTP 2xx when `start()` did not succeed.
