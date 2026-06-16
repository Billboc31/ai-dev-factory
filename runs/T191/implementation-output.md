All 41 tests pass. Here's a summary of what was done:

**Files modified:**

1. `services/control_api/services/project_id.py` — Added two guards at the top of `assert_contained` (before `.resolve()` is called):
   - `None` root → `ValueError("runtime_base_root is not configured")`
   - Empty/dot root (`""` or `"."`) → `ValueError(f"invalid runtime_base_root: {runtime_root!r}")`

2. `tests/test_project_id.py` — Added three regression tests in a new `# ── assert_contained — invalid base root ──` section covering `None`, `Path("")`, and `Path(".")`.

**Verified:**
- `test_project_bootstrap.py` already uses `tmp_path / "runtime"` throughout — no changes needed.
- 41/41 tests pass.
