# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T190/reviews/implementation-review.md
- generated at: 2026-06-16T12:51:30Z

---

I have a complete picture of the implementation. Here is the formal review.

---

## Review — T190: Fix supervisor runtime base resolution for project bootstrap

### Summary

The implementation correctly resolves the core failure: the supervisor no longer attempts to create directories under `/runtime/projects/<id>/...`. All five acceptance criteria are substantively met. The architecture is clean, well-scoped, and the new code paths are properly covered by tests.

---

### 1. Correctness relative to ticket requirements

**AC1 — No `/runtime/projects/` paths during bootstrap** ✓

`_runtime_base_root()` (`supervisor/main.py:71`) replaces the old hardcoded path. Bootstrap now creates `{runtime_base_root}/{project_id}/{dirs}` with no `/projects/` segment. `test_bootstrap_runtime_dirs_under_runtime_base_root` verifies this explicitly.

**AC2 — Runtime dirs under `RUNTIME_BASE_ROOT/<project_id>`** ✓

Resolution order is correctly implemented:
1. `RUNTIME_BASE_ROOT` env var
2. Parent of `AI_DEV_FACTORY_RUNTIME_ROOT`
3. `~/runtime` (safe local fallback — never `/runtime`)

`test_bootstrap_uses_parent_of_factory_runtime_root_when_no_base` covers the second path.

**AC3 — Structured error for missing/unwritable root (supervisor)** ✓

The pre-flight check at `main.py:1573` uses `os.access()` before mkdir and returns 422 `runtime_base_root_not_writable`. The `OSError` catch at line 1597 provides a second-layer return of 422. `test_bootstrap_not_writable_runtime_base_returns_422` validates this.

**AC4 — No unhandled OSError reaching the user** — Partially met with a residual gap (see below).

**AC5 — Diagnostic logs** ✓

The `logger.info` at `main.py:1562` logs all four required fields: `project_id`, `project_root`, `runtime_base_root`, `project_runtime_root`.

**AC6 — Existing ai-dev-factory runtime unaffected** ✓

`_runtime_base_root()` resolves to the parent of the existing `AI_DEV_FACTORY_RUNTIME_ROOT`, so the existing `/Users/pierrebocquet/runtime/ai-dev-factory` is untouched.

---

### 2. Issue: `runtime_base_root_not_writable` propagated as 500 through control_api

**Location:** `services/control_api/services/project_bootstrap.py:79-90`

When the supervisor returns `{"error": "runtime_base_root_not_writable"}`, the control_api `bootstrap()` function falls through to:

```python
raise RuntimeError(f"bootstrap failed: {detail}")
```

This is not caught by the `ValueError` handler in `routes/projects.py:166`, so it hits the generic `Exception` handler at line 168 and returns **500** to the end user, with the OSError detail string embedded in the body.

The supervisor itself returns 422 correctly (AC3 is met). But a user calling the control_api `/projects/import` endpoint for a misconfigured runtime root still receives a 500, which does not fully satisfy the "no unhandled error reaches the user" intent.

**Fix:** Add a mapping in `project_bootstrap.py`:

```python
if error_code == "runtime_base_root_not_writable":
    raise ValueError(f"runtime base root is not writable: {detail}")
```

This is a one-line fix. The corresponding test would call the control_api import endpoint (not the supervisor directly) with an unwritable runtime base and assert 422.

---

### 3. Pre-existing observation (not introduced by T190)

`resolve_state_dir` (`runtime_resolver.py:71`) has a last-resort fallback `return project_root / "runs"` — clearly a copy-paste from `resolve_runs_dir`. This was present before this ticket and is not a T190 regression. With `project_runtime_root` now being persisted and passed from bootstrap, this fallback is rarely reachable in practice.

---

### 4. Scope and quality

- Changes are well-bounded: supervisor path logic, project registry persistence, resolver functions, and routes. No unintended scope drift.
- `validate_project_id` + `assert_contained` provide path-traversal safety before any filesystem operation.
- The persisted `project_runtime_root` in `workspace.json` correctly decouples runtime paths from env var changes after first import.
- Test coverage is solid: 29 supervisor tests, registry persistence tests, and bootstrap service tests all target the new behaviors.

---

### Verdict

The core fix is correct, the architecture is clean, and all acceptance criteria are met at the supervisor level. The single actionable gap — the control_api propagating `runtime_base_root_not_writable` as 500 instead of 422 — does not change the fundamental correctness of the supervisor fix, but it leaves end users with an opaque error in the misconfigured-root case. The fix is trivial (one extra `if` branch in `project_bootstrap.py`).

IMPLEMENTATION_FIX_REQUIRED
