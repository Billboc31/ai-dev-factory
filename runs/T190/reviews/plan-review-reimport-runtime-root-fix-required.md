# Plan review — re-import runtime root fix required

The revised T190 plan is almost acceptable, but it must explicitly cover re-import/idempotency.

## Missing requirement

If a project already exists in the registry and already has a persisted `project_runtime_root`, re-importing or re-bootstraping the same project must reuse the existing `project_runtime_root`.

It must not compute a new path from current environment variables.

## Why this matters

Without this rule, changing `RUNTIME_BASE_ROOT` or `AI_DEV_FACTORY_RUNTIME_ROOT` after first import could silently move future operations to a different runtime path.

That would create inconsistent state:

- existing runs/logs/worktrees in the original runtime
- new daemon/worktree/log operations in another runtime
- project registry possibly overwritten with a new runtime root

## Required behavior

During import/bootstrap:

1. Check whether the project already exists in `ProjectRegistry`.
2. If it exists and `project_runtime_root` is set, reuse it.
3. Do not recompute or overwrite it unless an explicit future migration command exists.
4. If the path no longer exists, return a clear error asking for migration/repair, not silent recreation elsewhere.

## Acceptance additions

- Re-importing the same project preserves the original `project_runtime_root`.
- Changing `RUNTIME_BASE_ROOT` after initial import does not change existing project runtime roots.
- Bootstrap is idempotent for an already-registered project.
- Tests cover first import, API restart, and re-import with a different env var.

## Review verdict

PLAN_FIX_REQUIRED until this idempotency rule is included in `runs/T190/plan.md`.
