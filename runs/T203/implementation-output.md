All implementation complete and tests passing. Here is a summary of what I did:

## Files created
- `tools/agent_runner/ticket_diagnostics.py` — read-only diagnostic service with `diagnose_ticket()`, 11 per-check helpers, recommended-action catalog (15 keys), dedup, persist
- `services/control_api/routes/diagnostics.py` — `GET /tickets/{id}/diagnostics`, `POST /tickets/{id}/diagnostics/run` + project-scoped variants
- `apps/dashboard/src/components/TicketDiagnosticsPanel.jsx` — panel with stuck/healthy badge, severity, summary, checks list, recommended actions rendered as disabled buttons with "Action not wired yet" markers
- Tests: `tests/test_ticket_diagnostics_db.py` (7), `_service.py` (13), `_api.py` (5), `_safety.py` (4), plus `apps/dashboard/tests/TicketDiagnosticsPanel.test.jsx` (6)

## Files modified
- `tools/agent_runner/runtime_db.py` — added `ticket_diagnostics` table, `upsert_ticket_diagnostics`, `get_ticket_diagnostics`, postgres rebinding
- `tools/agent_runner/runtime_db_pg.py` — mirrored schema + helpers with project-scoped composite PK and JSONB casts
- `services/control_api/models/schemas.py` — added `DiagnosticCheck`, `DiagnosticRecommendedAction`, `TicketDiagnostics`
- `services/control_api/main.py` — wired both routers
- `apps/dashboard/src/api/tickets.js` — `getTicketDiagnostics`, `runTicketDiagnostics`
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — mounted `TicketDiagnosticsPanel`

## Verifications
- 29 new Python tests pass; 79 adjacent existing tests (readiness/rules/approvals/human-approval/pg-migration) pass with no regressions
- 6 new Vitest tests pass; existing intelligence/rules/board/list panel tests pass
- `TicketDetailPage.test.jsx` failures (3) and `test_control_api_endpoints.py` failures (10) reproduce on the pre-change branch — pre-existing, not regressions

## Design notes
- Service never imports/uses any mutating helper (`worktree_manager.remove*`, `runtime_checkpoint.reset*`, `ticket_approval_service.approve_*/reject_*`, `run_ticket.*`, `run_step.*`, `run_daemon.*`); enforced by `test_ticket_diagnostics_safety.py` allow-listing only read + persist helpers
- All Git subprocess calls bounded with `timeout=timeout_s`; any failure collapses to `unknown`
- Recommended actions deduplicated by `action_key` preserving first reason
- `_DONE_STATES` softens branch + worktree checks when ticket has completed (branch deleted post-merge is expected)
