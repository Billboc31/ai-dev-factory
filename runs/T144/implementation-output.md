Implementation is complete. Here's a summary of everything that was built:

---

**Files created (5 new):**
- `ai/roles/conflict-resolver.md` — Role definition for the AI conflict resolver
- `prompts/generic/conflict-resolver.md` — Generic task prompt template
- `tools/agent_runner/conflict_context_collector.py` — Assembles ticket.md, plan.md, reviews, PR diff, merge-base diff, conflicted files into `conflict/context.md`
- `tools/agent_runner/run_conflict_resolver.py` — Executor: fetch → rebase → AI resolver → stage → continue rebase → tests → commit → push `--force-with-lease` → state transition

**Files modified (10):**
- `tools/agent_runner/run_ticket.py` — Added `CONFLICT_RESOLVING` + `CONFLICT_RESOLVED_REVIEW_NEEDED` to `VALID_STATES`, added `reject-conflict-resolution` to `HUMAN_APPROVAL_TRANSITIONS`, added `apply_approve_conflict_resolution()`, added `--approve/reject-conflict-resolution` CLI flags
- `tools/agent_runner/run_step.py` — Registered `conflict-resolver` in aliases, default outputs, role files, skill files
- `services/control_api/models/schemas.py` — Added `resolution_summary` and `conflict_test_result` to `TicketSummary`
- `services/control_api/services/artifact_reader.py` — Updated `_conflict_fields()` to read `conflict/resolution.md` and `conflict/test-report.md`; added new states to `_STATUS_MAP`
- `services/control_api/services/subprocess_runner.py` — Added `resolve_conflicts()`, `approve_conflict_resolution()`, `reject_conflict_resolution()`
- `services/control_api/routes/tickets.py` — Added 3 endpoints (`/resolve-conflicts`, `/approve-conflict-resolution`, `/reject-conflict-resolution`) + 3 project-scoped variants + `_transition_to_resolving()` helper
- `apps/dashboard/src/api/tickets.js` — Added `resolveConflicts`, `approveConflictResolution`, `rejectConflictResolution`
- `apps/dashboard/src/pages/TicketsPage.jsx` — Added yellow/blue badge styles for `CONFLICT_RESOLVING`/`CONFLICT_RESOLVED_REVIEW_NEEDED`; expanded `CONFLICT_STATES` set
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — Added `ConflictResolutionPanel` component with state-conditional UI for all 4 conflict states
- `tests/test_human_approval.py` — Updated count/keys assertions to include new `reject-conflict-resolution` entry
