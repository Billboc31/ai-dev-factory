I now have everything I need. Let me write the review.

---

## Review — T189: Project bootstrap must create a dedicated runtime root per project

### Summary

The implementation refactors runtime root resolution from a hardcoded `/runtime/projects/<project_id>` pattern to a configurable `<RUNTIME_BASE_ROOT>/<project_id>` model. The core goal of the ticket is met: project import no longer attempts to write to `/runtime` and each project gets an isolated, correctly located runtime root.

---

### Acceptance criteria verification

| Criterion | Status | Evidence |
|---|---|---|
| No code writes to `/runtime/projects/...` | ✅ | `"projects/"` subdirectory removed from all path constructions |
| Runtime root is `$RUNTIME_BASE_ROOT/<project_id>` | ✅ | `supervisor/main.py:1542`, `routes/projects.py:84` |
| Bootstrap creates all 5 dirs (clones, worktrees, runs, state, logs) | ✅ | `supervisor/main.py:1550-1551` |
| AI Dev Factory isolated from imported projects | ✅ | Sibling layout, separate base roots |
| Multiple projects coexist independently | ✅ | `test_bootstrap_sibling_isolation` |
| Path traversal prevented | ✅ | `assert_contained()` in `project_id.py:52-67` |

---

### Correctness

**Control API** (`main.py:70-81`): Three-tier fallback for `RUNTIME_BASE_ROOT` (`RUNTIME_BASE_ROOT` env var → parent of `AI_DEV_FACTORY_RUNTIME_ROOT` → `~/runtime`) is coherent and backward compatible.

**Supervisor** (`main.py:1604-1618`): `_runtime_base_root()` mirrors the same three-tier resolution. Per-project helper functions (`_project_runtime_root`, `_project_runs_dir`, etc.) all derive correctly from it.

**Containment check** (`project_id.py:52-67`): `assert_contained()` uses `.resolve()` + string prefix to prevent path traversal. Correct.

**List projects** (`routes/projects.py:84`): `runtime_base_root / p.name` — `"projects/"` subdirectory correctly removed.

---

### Issues

#### Observation 1 — Dead `runtime_root` field in POST body

`project_bootstrap.py:74` sends `"runtime_root": str(runtime_base_root)` to the supervisor. The supervisor's `ProjectBootstrapHostRequest` accepts this field (`main.py:1473`) but **completely ignores it** at `main.py:1542`, re-resolving from env vars instead.

The test itself acknowledges this: `# ignored by supervisor; kept for compat` (test line 171).

Consequence: if `RUNTIME_BASE_ROOT` is set in the control API container but not in the supervisor container, `assert_contained()` validates against a different path than where the supervisor actually creates directories. The response `runtime_root` field will reflect the supervisor's actual path, but the paths could silently diverge in a misconfigured deployment. This is an operational footgun, not a correctness bug, but the misleading field name (`runtime_root` carries a value that is actually `runtime_base_root`) adds confusion.

**Severity**: Low (works correctly in the intended deployment model).

#### Observation 2 — `test_bootstrap_creates_runtime_directories` creates real directories in `~/runtime`

`tests/test_supervisor_projects.py:85-99` does not `monkeypatch.setenv("RUNTIME_BASE_ROOT", ...)`, so the supervisor resolves to `~/runtime` and creates `~/runtime/my-project/{runs,logs,state,worktrees,clones}` on the actual test runner filesystem. These directories are not cleaned up after the test. The subsequent test (line 162) correctly uses `monkeypatch` to isolate, but this first test is not isolated.

**Severity**: Minor. Tests pass but leave artifacts.

#### Observation 3 — Pre-existing `resolve_state_dir` fallback bug (not introduced by T189)

`runtime_resolver.py:58`: `return project_root / "runs"` — the last fallback of `resolve_state_dir` returns `runs/` instead of `state/`. This bug predates T189; the diff only added the `RUNTIME_BASE_ROOT` branch without fixing the fallback. Only triggers in the bare no-env-vars case.

**Severity**: Pre-existing, not a T189 regression.

---

### Code quality

- Naming is internally consistent: `runtime_base_root` (base) vs `runtime_root` (per-project) throughout control API and supervisor helper functions.
- `BootstrapResult` dataclass and Pydantic schema both updated with `clones_dir` field.
- `resolve_project_runtime_root()` correctly renamed from `runtime_root` to `runtime_base_root` parameter.
- `.env.example` clearly explains the new variable and its relationship to `AI_DEV_FACTORY_RUNTIME_ROOT`.

---

### Conclusion

The implementation is correct and complete relative to the ticket requirements. All acceptance criteria are satisfied. The two observations above are non-blocking: one is an operational concern about env var alignment between services (not a code bug), the other is a test isolation gap that doesn't affect correctness. The pre-existing fallback bug is explicitly out of scope.

IMPLEMENTATION_APPROVED
