# Plan review — T134

Decision: PLAN_FIX_REQUIRED

The current T134 plan is too ambitious for one safe ticket.

It jumps directly to a full AI fix loop:

- failed deploy detection
- AI-generated script fixes
- applying file patches
- committing and pushing fixes
- redeploy retries
- fix loop history
- new fix_loop router
- dashboard iteration UI

This is valuable, but it should come after a simpler sandbox deploy validation workflow exists.

## Requested change

Rewrite T134 as a V1 focused on the Deployer user workflow:

> Deploy & Test in Sandbox

The goal is to let the user click a button in the Deployer page that creates an isolated sandbox, runs the generated operational scripts, executes the healthcheck, captures logs, and reports success/failure.

Do not implement AI auto-fix yet.

See `runs/T134/fixes/plan-fix-1.md` for the requested reduced scope.
