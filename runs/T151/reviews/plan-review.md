# Plan review — T151

Decision: PLAN_FIX_REQUIRED

The current plan correctly identifies the need for a dedicated Environments / Deployments dashboard, but it is too broad and introduces a second orchestration stack parallel to the existing sandbox runtime.

## Main concern

The plan proposes new backend primitives:

- `EnvironmentManager`
- `run_environment.py`
- new supervisor environment routes
- a new environment port registry
- a new deployment state model
- a new worker lifecycle

This duplicates existing capabilities already present or being built in the sandbox runtime:

- isolated worktrees
- isolated ports
- compose project isolation
- proxy URLs
- lifecycle modes
- undeploy/cleanup
- supervisor-side execution
- sandbox run state

Duplicating this stack will create long-term divergence between:

- sandbox deploy pipeline
- environment deploy pipeline

That should be avoided.

## Required direction

T151 should be an environment-management UX/API layer built on top of the existing sandbox/runtime lifecycle.

It should NOT create a separate deployment engine.

See `runs/T151/fixes/plan-fix-1.md` for the requested reduced/refactored scope.
