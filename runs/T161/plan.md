Now I have a thorough understanding of the codebase. Let me produce the plan.

---

## Objective

Fix `create_environment()` so that when docker provisioning fails after `SandboxManager.create()`, the partially-created sandbox is destroyed and an HTTP 500 is returned — preventing fake environment cards from appearing in the UI. Add tests covering the full provisioning contract.

## Included

### `services/control_api/routes/environments.py`

Rewrite the `create_environment()` post-create block (lines 114–118):

**Current (broken):**
```python
try:
    state = mgr.start(state.id)
except Exception as exc:
    logger.warning("environment start failed after create: %s", exc)
return state
```

**Target behaviour:**
1. Call `mgr.start(state.id)`.
2. On any exception from `start()`, call `mgr.destroy(state.id)` (best-effort), then raise `HTTPException(status_code=500, detail="environment provisioning failed: …")`.
3. If `start()` returns without exception but `state.status == SandboxStatus.error`, call `mgr.destroy(state.id)` and raise the same 500. This is the critical path: docker compose `up` failure does not raise — it sets `status=error` silently.
4. Only return HTTP 201 when `started.status == SandboxStatus.running`.

A thin private helper `_destroy_silently(mgr, sandbox_id)` handles the cleanup so the route stays readable.

### `tests/test_environment_routes.py`

Add the following new test cases (all use `tmp_path`, monkeypatch `subprocess.run`):

| Test name | What it asserts |
|---|---|
| `test_create_environment_creates_real_sandbox_dir` | `{sandboxes_dir}/{env_id}/` exists on disk after a successful create |
| `test_create_environment_creates_state_json` | `{sandbox_dir}/state.json` exists and is valid JSON after create |
| `test_create_environment_creates_env_file` | `{sandbox_dir}/.env` exists after create |
| `test_failed_provisioning_returns_500` | Mock compose `up` to return `returncode=1`; POST returns 5xx |
| `test_failed_provisioning_no_environment_card` | After the same failure, `GET /environments` lists zero envs |
| `test_failed_provisioning_sandbox_dir_removed` | After the same failure, the sandbox directory is removed |
| `test_create_environment_sandbox_id_from_manager` | Response `id` is a 12-char lowercase hex string (real sandbox id, not env_name) |
| `test_environment_actions_work_after_create` | After successful create, redeploy / stop / refresh / delete all return non-5xx |

### Scope of changes

Only two files are modified:
- `services/control_api/routes/environments.py` — error-handling logic only (no new routes, no signature changes)
- `tests/test_environment_routes.py` — new test functions appended

## Excluded

- Modifying `SandboxManager.start()`, `create()`, `destroy()`, or any other SandboxManager method.
- Changes to any other route (sandboxes, jobs, agents, etc.).
- UI/frontend changes.
- Git ref resolution, worktree flows, or deploy profiles.
- Adding a separate validation method to SandboxManager.
- Any database or persistence-layer changes.

## Acceptance criteria

- `POST /environments` with a healthy docker returns HTTP 201 and `status == "running"`.
- `POST /environments` when docker compose up fails returns HTTP 5xx (not 201 with a fake card).
- After a failed create, `GET /environments` returns an empty list (no leftover card).
- After a failed create, the sandbox directory under `sandboxes_dir` does not exist.
- After a successful create, `{sandbox_dir}/state.json` and `{sandbox_dir}/.env` both exist.
- The response `id` is a 12-character hex string, not the environment name.
- All existing tests continue to pass unchanged.
- All new tests listed above pass.
