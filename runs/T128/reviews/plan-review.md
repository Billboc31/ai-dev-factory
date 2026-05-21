# Plan review — T128

Decision: PLAN_FIX_REQUIRED

The current plan is directionally good, but it is not safe or precise enough for approval.

Problems:

- The plan is written as a summary, not as a full implementation plan.
- It does not clearly use the expected Objective / Included / Excluded / Acceptance criteria structure.
- It combines too much in one ticket: host supervisor, job registry, dependency checks, file locking, dashboard changes, Docker configuration, daemon delegation and deployment-job foundations.
- The host supervisor is a critical runtime component; it should be introduced in a smaller V1 before adding job registry complexity or deployment orchestration.

Requested action:

Rewrite T128 as a minimal host-supervisor V1.

The goal of V1 is only to prove that the Docker control API can delegate daemon start/stop/status to a real host-side supervisor, instead of trying to spawn the daemon inside Docker.

See `runs/T128/fixes/plan-fix-1.md` for the requested reduced scope.
