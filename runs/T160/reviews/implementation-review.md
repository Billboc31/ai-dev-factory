Now I have everything I need for a complete review.

---

## Review — T160: Fix environment sandbox path resolution and runtime root handling

### Scope compliance

The implementation is fully bounded to the ticket. No unrelated refactors, no new dependencies, no dashboard changes (correctly excluded with justification).

---

### Correctness vs ticket requirements

**Path resolution — PASS**

`_env_file_path(sandbox_id)` and `_runtime_root_path(sandbox_id)` are private helpers that derive exclusively from `self.sandboxes_dir` (line 119–123). Every call site that previously read `state.env_file` or `Path(state.sandbox_runtime_root)` now routes through these helpers:

| Operation | Before | After |
|---|---|---|
| `_run_compose` | `state.env_file` | `_env_file_path(sandbox.id)` |
| `logs` | would have used `state.env_file` | `_env_file_path(sandbox_id)` |
| `stop` | `Path(state.sandbox_runtime_root)` | `_runtime_root_path(sandbox_id)` |
| `_start_sandbox_supervisor` | `Path(state.sandbox_runtime_root)` | `_runtime_root_path(state.id)` |
| `_terminate_sandbox_supervisor` | stored path | `_runtime_root_path(state.id)` |
| `destroy` | stored paths | both helpers |

**Remove hardcoded `/sandboxes` — PASS**

The static test `test_no_hardcoded_sandboxes_path_in_sandbox_manager` (line 321) asserts zero `Path("/sandboxes")` and `"/sandboxes/"` occurrences in `sandbox_manager.py`. Code inspection confirms this. `runtime_resolver.py` uses `Path.home() / "sandboxes"` as a fallback default (correct; not a hardcoded absolute path).

**`infra_service_manager.py` structural check — PASS**

`resolve_host_runtime_root()` line 118: `not p.is_relative_to(get_sandbox_root())` replaces the fragile `"sandboxes" not in p.parts`. This correctly handles any `SANDBOX_ROOT` value.

**Metadata model — PASS**

`env_file: str = ""` in `sandbox.py` line 44 is optional with a default and marked informational. The field is kept for wire-format backwards compatibility without being used operationally.

**Error handling — PASS**

`_read_state` (line 125–130) catches `FileNotFoundError` and raises `SandboxNotFoundError`. All six route handlers catch `SandboxNotFoundError` and return `HTTP 404` with `"environment not found: <id>"`. No raw OS tracebacks reach the client.

---

### Test coverage

Six new tests are present. Spot-checking key ones:

- `test_path_helpers_use_sandboxes_dir` (line 393): verifies helpers resolve under configured dir — correct.
- `test_stop_uses_helper_path_ignoring_stale_env_file` (line 402): poisons `state.env_file` with `/wrong/stale/path/.env`, then asserts the command line uses a path under `sandboxes_dir` — directly covers the root cause.
- `test_missing_sandbox_returns_readable_404` (line 303): confirms GET and POST /stop return 404 with `"environment not found"` — no 500.
- `test_no_hardcoded_sandboxes_path_in_sandbox_manager` (line 321): static grep assertion.

---

### Minor observations (non-blocking)

**1. `test_custom_sandbox_root_resolves_correctly` gaps vs plan**

The plan specified testing redeploy and logs in the custom-root scenario. The test (line 275) covers create + stop + delete only. Redeploy (`/redeploy`) and logs (`/logs`) are not exercised. This is a test coverage gap but the path helper unit tests cover the underlying mechanism.

**2. DELETE is idempotent (204 for non-existent sandbox)**

`destroy()` (line 449) catches `SandboxNotFoundError` internally and silently exits. As a result, `delete_environment` in `routes/environments.py` (line 154) will always return 204 regardless of whether the sandbox existed. The route handler's `except SandboxNotFoundError` block is unreachable for DELETE. This is intentional REST-idempotent behavior (reasonable for DELETE) but the plan stated "missing sandboxes return explicit API errors" without carving out DELETE. The test for missing-sandbox error only covers GET and /stop, so this is untested and slightly inconsistent with the plan's wording — not a regression and not a blocker.

**3. `logs()` duplicates subprocess setup instead of using `_run_compose`**

`logs()` (line 515) builds the docker compose command inline rather than calling `_run_compose`. Pre-existing pattern, not introduced here, no correctness impact.

---

### Verdict

The root cause — runtime actions reconstructing paths from stale stored state instead of through the runtime resolver — is correctly and completely fixed. All acceptance criteria are satisfied. The two observations above are minor and do not affect correctness or safety.

IMPLEMENTATION_APPROVED
