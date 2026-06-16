Now I have a complete picture. Here is the implementation plan.

---

## Objective

Guard `assert_contained` against an uninitialised or effectively-empty `runtime_base_root` so that a missing configuration returns a clear configuration error instead of a misleading workspace-escape error.

## Included

### `services/control_api/services/project_id.py`

Add a guard at the top of `assert_contained` (before line 60 where `.resolve()` is called):

- If `runtime_root is None` → raise `ValueError("runtime_base_root is not configured")`
- If `str(runtime_root) in ('', '.')` (covers `Path('')` / `Path('.')`, both of which silently resolve to CWD) → raise `ValueError(f"invalid runtime_base_root: {runtime_root!r}")`

No other logic in the function changes.

### `tests/test_project_id.py`

Add a new section `# ── assert_contained — invalid base root ──` with three regression tests:

- `test_assert_contained_raises_on_none_root` — calls `assert_contained(None, "test-ai-dev")`, expects `ValueError` mentioning "not configured"
- `test_assert_contained_raises_on_empty_root` — calls `assert_contained(Path(""), "test-ai-dev")`, expects `ValueError` mentioning "invalid runtime_base_root"
- `test_assert_contained_raises_on_dot_root` — calls `assert_contained(Path("."), "test-ai-dev")`, expects `ValueError` mentioning "invalid runtime_base_root"

Existing `assert_contained` tests already use `tmp_path`; no changes needed there.

### `tests/test_project_bootstrap.py`

Audit every test to confirm `runtime_base_root = tmp_path / "runtime"` is used (the file already follows this pattern throughout). If any test is found using `Path("")` or `Path(".")` as base, fix it. (Based on current read, all tests already use `tmp_path / "runtime"` — this is a verification step, not expected to require changes.)

No changes to `runtime_resolver.py`, `project_bootstrap.py`, the supervisor, or any route layer — the guard in `assert_contained` is the single, centralised fix point.

## Excluded

- Changing the supervisor's `_runtime_base_root()` resolution logic.
- Adding `runtime_base_root` validation to individual callers (`bootstrap()`, `resolve_project_runtime_root()`) — the guard in `assert_contained` is the authoritative place.
- Fixing any other unrelated test failures not caused by the invalid-base-root bug.
- Changing the public API or return types of any function.
- Adding `None` to the `runtime_root: Path` type hint (callers already pass `Path`; the None check is a runtime defence only).

## Acceptance criteria

- `assert_contained(None, "test-ai-dev")` raises `ValueError` with a message containing "not configured", not "would escape".
- `assert_contained(Path(""), "test-ai-dev")` and `assert_contained(Path("."), "test-ai-dev")` raise `ValueError` with a message containing "invalid runtime_base_root", not "would escape".
- `assert_contained(tmp_path / "runtime", "test-ai-dev")` returns `tmp_path / "runtime" / "test-ai-dev"` (existing happy path unchanged).
- No path `/test-ai-dev` (or any `/<project_id>` rooted at `/`) is produced by `assert_contained` for a valid `project_id` when `runtime_base_root` is legitimately configured.
- `pytest tests/test_project_id.py tests/test_project_bootstrap.py` passes in full.
