I now have everything needed for a complete review.

---

## Implementation Review — T191

### Correctness vs. Ticket Requirements

**Requirement 1 — Validate `runtime_base_root` before containment checks**

Two guards added at the top of `assert_contained()` (`project_id.py:59-62`), before `.resolve()` is called:

```python
if runtime_root is None:
    raise ValueError("runtime_base_root is not configured")
if str(runtime_root) in ("", "."):
    raise ValueError(f"invalid runtime_base_root: {runtime_root!r}")
```

Order is correct: guards fire before `validate_project_id()` and before `runtime_root.resolve()`, which would silently produce `/` or CWD-rooted paths. ✅

**Requirement 2 — Improve error reporting**

Error messages match the ticket specification exactly:
- `None` → `"runtime_base_root is not configured"` ✅
- Empty/dot → `"invalid runtime_base_root: ''"` / `"invalid runtime_base_root: '.'"` ✅

**Requirement 3 — Fix tests**

`test_project_bootstrap.py` already uses `tmp_path / "runtime"` throughout all 14 tests (lines 44, 55, 71, etc.) — no change needed, confirmed. ✅

**Requirement 4 — Add regression coverage**

Three new tests in `test_project_id.py:148-160`:
- `None` root → raises `"not configured"` ✅
- `Path("")` → raises `"invalid runtime_base_root"` ✅
- `Path(".")` → raises `"invalid runtime_base_root"` ✅

Valid root + bootstrap path creation already covered by pre-existing tests. ✅

### Acceptance Criteria

| Criterion | Status |
|---|---|
| No valid project_id produces `/test-ai-dev` | ✅ guards block invalid bases before path construction |
| Missing runtime config returns a config error | ✅ `ValueError("runtime_base_root is not configured")` |
| `assert_contained` always receives valid base root | ✅ early rejection of None/empty/dot |
| Full test suite passes | ✅ 41/41 |

### Scope Compliance

Only two files modified: `services/control_api/services/project_id.py` and `tests/test_project_id.py`. No callers were changed, no type hints modified, no supervisor logic touched. Change is strictly bounded to the ticket. ✅

### Observations (non-blocking)

- The `runtime_root: Path` type hint accepts `None` at runtime, which works correctly but is technically a type mismatch. The plan explicitly acknowledged this as a deliberate runtime-defence-only guard — acceptable.
- `Path("/")` (filesystem root) is not guarded, but that case is not part of the described failure mode and not in scope.

### Conclusion

The implementation is minimal, correctly placed, clearly named, and closes all ticket-specified failure modes with direct regression coverage. No blocking issues.

IMPLEMENTATION_APPROVED
