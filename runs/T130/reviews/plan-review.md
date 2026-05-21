# Plan review — T130

Decision: PLAN_FIX_REQUIRED

The plan is strong, but the execution location is wrong.

The current plan runs the AI analysis process directly from the control API.

That is not correct when the API runs inside Docker because it may not have access to the host AI runtime, gh, git worktrees, credentials, or the canonical runtime environment.

Requested fix:

Rewrite the plan so the dashboard/control API delegates Analyze Project to the host supervisor.

The supervisor should launch the host-side analysis job. The control API should only trigger it, read status, read logs, and display results.

See runs/T130/fixes/plan-fix-1.md for the reduced architectural correction.
