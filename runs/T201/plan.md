Rewrote `runs/T201/plan.md` from scratch as a real implementation plan. It opens with the title and the four mandatory level-2 headings in order (`## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`), with `## Included` split into `### Database`, `### Rules engine`, `### Supported rules`, `### Default policy`, `### API`, `### Frontend`, `### Tests`.

Key invariants pinned in the plan content (not as a meta-summary):
- `require_human_approval` resolves through `get_execution_approval_state(...) == "ready_to_take"`, which wraps `compute_execution_eligibility(...)`; rule handlers are forbidden from touching `ticket_approvals`, enforced by a static grep test.
- Default policy enables the four `require_*` / `block_when_*` rules and disables both threshold rules.
- Acceptance criterion #10 plus `tests/test_execution_rules_pipeline_untouched.py` assert `run_daemon.py`, `run_ticket.py`, and the scheduler are untouched.
