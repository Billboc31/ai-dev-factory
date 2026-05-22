# Plan review — T138

Decision: PLAN_FIX_REQUIRED

The current T138 plan is too ambitious for a first auto-fix iteration.

It combines in a single ticket:

- AI orchestration
- async supervisor runtime
- automatic patch application
- sandbox reruns
- retry loops
- iteration persistence
- dashboard orchestration UI
- history endpoints
- AI provider integration
- automatic convergence logic

This should be split into smaller runtime-safe steps.

The first implementation should focus on a safe and observable dry-run proposal workflow.

Do not automatically modify operational artifacts or rerun sandboxes yet.

See `runs/T138/fixes/plan-fix-1.md`.
