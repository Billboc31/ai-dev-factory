# Plan review — T139

Decision: PLAN_FIX_REQUIRED

The current T139 plan is too large for one safe ticket.

It includes in one implementation:

- a new full runtime dashboard page
- many backend endpoints
- sandbox rerun
- sandbox stop
- proposal patch viewer
- runtime health aggregation
- global stale worktree cleanup
- global stale sandbox cleanup
- orphan pid/lock cleanup
- destructive cleanup flows
- frontend log polling
- backend and frontend tests

This is valuable, but too much for a first runtime operations UI.

The first version should be mostly read-only and safe, with only very limited cleanup.

See `runs/T139/fixes/plan-fix-1.md` for the reduced V1 scope.
