The plan at `runs/T201/plan.md` is fully rewritten from scratch as a real implementation plan (not a meta-report).

Structure:
- `# T201 Execution Rules Engine` title, then the four mandatory level-2 headings in order: `## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`.
- `## Included` is broken into `### Database`, `### Rules engine`, `### Supported rules`, `### Default policy`, `### API`, `### Frontend`, `### Tests`.

Key correctness points addressed from the review/fix:
- `require_human_approval` is pinned to `compute_execution_eligibility(...) == "ready_to_take"` via the local `get_execution_approval_state` wrapper. Direct rule-level reads of `ticket_approvals` are forbidden, and acceptance criterion #4 plus a grep test in `test_execution_rules_engine.py` enforce the invariant.
- Default policy enables exactly the four `require_*`/`block_*` rules and disables the two thresholds (`max_estimated_cost_usd`, `max_difficulty`), spelled out explicitly.
- All six rule keys listed; SQLite and Postgres DDL both included; routes mirror the dual `router` / `project_router` pattern of `readiness.py`; POST returns 202; tests use the `_isolate_env` / `_make_app` / `_make_ticket` fixture pattern.
- Scheduler isolation enforced by `## Excluded` naming `run_daemon.py`/`run_ticket.py` and acceptance criterion #10 (a `git diff` assertion).
