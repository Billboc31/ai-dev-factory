Plan rewritten at `runs/T201/plan.md` with the four mandatory headings (`## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`). The previous file was a status report and would have failed the validator.

Key design points carried through from the review/fix instructions:
- `require_human_approval` and `block_when_human_review_required` both go through `ticket_approval_service.compute_execution_eligibility` via a thin `get_execution_approval_state` wrapper — no direct `ticket_approvals` reads.
- Default policy listed explicitly: four enabled rules, two disabled threshold rules.
- Failure reasons are human-readable per-rule.
- Scheduler/daemon/worker paths are explicitly excluded; engine remains advisory-only.
