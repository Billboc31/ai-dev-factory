The updated `runs/T190/plan.md` is written. Here is what changed from the previous version:

**New in `## Included`:**
- `project_bootstrap.py` now has an explicit 4-step idempotency protocol: check registry first → reuse persisted root if found → return structured error if path is gone → write root only on first bootstrap.
- Tests expanded to cover three new scenarios: API restart round-trip, re-import with changed env var, and re-import with missing path.

**New in `## Acceptance criteria`:**
- Re-import preserves the original `project_runtime_root` regardless of current env vars.
- Re-import with a missing path returns a structured error, not silent recreation.

The plan now satisfies both reviews (runtime base resolution contract + idempotency requirement). It is ready for PLAN_APPROVED.
