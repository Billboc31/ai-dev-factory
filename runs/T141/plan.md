The revised plan is written to `runs/T141/plan.md`. Here's a summary of what changed from the rejected plan:

**Dropped entirely:**
- Generic runtime topology model (`runtime_topology.py`, `ComponentType`, `ComponentHealth`)
- `sandbox-profile.yml` format and profile loading
- Component startup abstraction and health polling
- `tests/test_runtime_topology.py`

**Kept and grounded to actual code:**
- The plan now targets the exact files that need to change: `sandbox_manager.py`, `routes/sandbox.py`, `routes/runtime_dashboard.py`
- It reuses the existing `_terminate_sandbox_supervisor()` and `_release_slot()` already in `destroy()` — the real gap is that `stop()` doesn't call them
- The missing endpoints (`/restart`, `/refresh`) are clearly identified as absent from the current router
- `SandboxRunSummary` enrichment is scoped to just `runtime_root` and `uptime_seconds` (the two fields that serve lifecycle state visibility without topology abstractions)
- A single new test file covers all lifecycle scenarios
