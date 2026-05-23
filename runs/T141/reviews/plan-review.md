# Plan review — T141

Decision: PLAN_FIX_REQUIRED

The current T141 plan is too ambitious for one implementation ticket.

It combines:

- generic runtime topology model
- sandbox-profile.yml format
- component startup abstraction
- component health polling
- daemon/worker/database/redis/custom component handling
- lifecycle endpoints
- restart/destroy/preserve logs
- runtime dashboard enrichment
- multiple new test suites

These are valuable, but the immediate runtime need is simpler and more urgent: the user can start sandbox environments but cannot safely stop, restart, or clean them up from the UI.

## Requested change

Rewrite T141 as a focused V1:

> Sandbox lifecycle controls: stop, restart, cleanup/delete, refresh.

The ticket should focus on safe lifecycle operations for existing sandbox runs.

Do not introduce the generic topology model or sandbox-profile.yml in this ticket.

See `runs/T141/fixes/plan-fix-1.md` for the requested reduced scope.
