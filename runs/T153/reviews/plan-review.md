# Plan review — T153

Decision: PLAN_FIX_REQUIRED

The current direction is good, but the plan should be simplified before approval.

The long-term product goal is correct:

```text
Deployer = audit → generate/fix scripts → deploy ephemeral sandbox → healthcheck → smoke tests → auto-fix → retry → cleanup
```

However, implementing the full smoke-test layer and the complete auto-fix loop in one ticket is risky.

## Main concern

T153 must not become a large all-at-once implementation that mixes:

- smoke test generation
- smoke test execution
- AI patch generation
- AI patch application
- redeploy loop
- progress detection
- failure classification
- UI/state changes
- cleanup behavior

That is too much for a single safe implementation step.

## Required simplification

T153 should be split into a smaller V1 focused on:

1. adding a generic smoke-test lifecycle after healthcheck
2. executing `smoke.sh` when present
3. persisting healthcheck and smoke-test results separately
4. preparing iteration artifacts for a future auto-fix loop
5. optionally generating an AI fix proposal, but not applying it automatically yet

The full apply-patch-and-rerun auto-fix loop should be a follow-up ticket after smoke tests are stable.

See `runs/T153/fixes/plan-fix-1.md`.
