I have enough information to write the review. Let me now produce the structured review.

---

## Implementation Review — T188

**Branch:** `ticket/T188-t188-route-all-host-filesystem-project-import-and`  
**Files reviewed:** `services/supervisor/main.py`, `services/control_api/routes/projects.py`, `services/control_api/services/project_bootstrap.py`, `tests/test_supervisor_projects.py`, `tests/test_project_bootstrap.py`, `tests/test_auto_bootstrap.py`

---

### Summary

The implementation correctly achieves the architectural goal of the ticket: project import validation and bootstrap are now fully delegated to the supervisor. The Control API no longer performs direct host-filesystem checks during import. All 35 new tests pass.

---

### Correctness relative to ticket requirements

**Import flow (UI → Control API → Supervisor → host validation → persistence):**  
Implemented correctly. `routes/projects.py:_supervisor_validate_path()` calls `POST /projects/validate-path` on the supervisor before any persistence. The `import_project()` handler passes the supervisor-resolved path into `bootstrap()` rather than a raw user-supplied string.

**Bootstrap flow via supervisor:**  
`project_bootstrap.py:bootstrap()` is now a thin HTTP client. It calls `POST /projects/bootstrap`, maps supervisor error codes to `ValueError`/`RuntimeError`, then registers the project. No `mkdir`, `write_text`, `is_dir`, or `resolve` calls remain in this file. ✓

**Supervisor endpoints:**  
Both required endpoints exist:
- `POST /projects/validate-path` (supervisor/main.py:1476) — returns `{resolved_path, is_dir, is_git_repo, git_root}` or structured error
- `POST /projects/bootstrap` (supervisor/main.py:1510) — idempotent, creates runtime directories and `project.yml`

**Error codes:**  
`path_not_found`, `not_a_directory`, `git_not_found`, `permission_denied` are all returned correctly with HTTP 422.

**Idempotency:**  
`POST /projects/bootstrap` correctly skips writing `project.yml` if it already exists. `mkdir(parents=True, exist_ok=True)` makes directory creation idempotent. Verified by tests.

**auto_bootstrap():**  
Correctly delegates to supervisor when `runtime_root` is provided. Falls back gracefully (logs warning, still registers) when supervisor is unreachable. ✓

---

### Scope compliance

**In scope, correctly included:**
- `validate-path` and `bootstrap` supervisor endpoints ✓
- Stack detection moved to supervisor's `_detect_stack_for_path()` ✓
- Control API `import_project()` no longer calls `Path.exists()` or `Path.expanduser()` ✓
- Supervisor client helper `_call_supervisor()` in `project_bootstrap.py` ✓

**Plan exclusions respected:**
- `list_projects` / `_read_stack` / `_read_github_repo` / `_list_branches` were left unchanged (explicitly excluded from scope). These helpers still read host paths directly, but that was a declared exclusion.

**One orphaned file:**  
`services/control_api/services/stack_detector.py` has no remaining callers (grep confirmed: zero imports). The plan said it "may be deleted" — it was not. This is dead code but not harmful.

---

### Code quality and safety

**Two separate supervisor HTTP helpers:**  
`routes/projects.py` introduces `_supervisor_validate_path()` while `project_bootstrap.py` has `_call_supervisor()`. These are not shared. Minor duplication; they differ enough in interface (one raises `HTTPException`, the other returns a tuple) that sharing would complicate callers. Acceptable.

**Error handling gap — `_supervisor_validate_path()`:**  
The `return resp.json()` call is inside the `try` block but only `httpx.ConnectError` and `httpx.TimeoutException` are caught. If the supervisor returns a malformed (non-JSON) body, `resp.json()` raises a `json.JSONDecodeError` that propagates as an unhandled exception, producing an undescriptive 500. Minor robustness gap.

**Error handling gap — `_call_supervisor()`:**  
If the supervisor returns a 500 without `"error"` in the payload (FastAPI default `{"detail": "..."}`), the caller's `data["project_id"]` will `KeyError`. Same class of issue — minor, only occurs on supervisor bugs.

**No path traversal guard in supervisor `/projects/bootstrap`:**  
`body.project_id` flows directly into `runtime_root / "projects" / body.project_id` without sanitisation. The Control API defends this with `assert_contained()` before calling the supervisor, but the supervisor endpoint is not independently safe. Since the supervisor binds to `127.0.0.1:8090` (localhost-only, no auth), the attack surface is very low. Acceptable for current architecture but worth noting.

**`_supervisor_validate_path` does not handle `httpx.HTTPError`** (base class covering connection-reset, read-timeout variants not caught by the two specific subclasses). Unlikely to fire in practice; acceptable.

---

### Test coverage

35 tests, all passing:
- Supervisor endpoint tests cover: happy path, missing path, not-a-directory, non-git dir, worktree `.git` file, idempotency, stack detection, directory structure placement.
- `project_bootstrap.py` tests cover: correct paths, registry persistence, supervisor argument verification, duplicate ID rejection, unreachable supervisor, non-git/missing-path error mapping, path-traversal guard.
- `auto_bootstrap.py` tests cover: supervisor delegation, idempotency, `runtime_root=None` path, supervisor failure fallback, invalid ID.

No missing coverage for the core acceptance criteria.

---

### Acceptance criteria verification

| Criterion | Status |
|-----------|--------|
| Import `/Users/…` works when API runs in Docker | ✓ — supervisor does the filesystem check |
| Filesystem validation executes through supervisor | ✓ |
| Bootstrap executes through supervisor | ✓ |
| Control API makes no host filesystem assumptions in import path | ✓ |
| Existing imported projects continue to work | ✓ — `list_projects` unchanged |
| Multi-project workflow unchanged | ✓ — per-project daemon endpoints untouched |
| `project_bootstrap.py` has no `Path.mkdir/is_dir/resolve/write_text` | ✓ |
| `routes/projects.py:import_project()` has no `Path.exists()/expanduser()` | ✓ |

---

### Issues

**Blocking:** none.

**Minor (non-blocking):**
1. `services/control_api/services/stack_detector.py` is orphaned dead code — should be deleted in a follow-up.
2. `_supervisor_validate_path()` and `_call_supervisor()` could share a common supervisor HTTP helper, but the current duplication is harmless.
3. `json.JSONDecodeError` on malformed supervisor responses is unhandled in both callers — could produce undescriptive 500s on supervisor bugs.
4. Supervisor `/projects/bootstrap` has no independent path-traversal guard on `project_id`. Acceptable given localhost-only binding.

---

IMPLEMENTATION_APPROVED
