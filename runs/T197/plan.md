The plan is written to `runs/T197/plan.md`. Here is a summary of what it covers:

**Objective**: Hybrid advisory Ticket Intelligence Analyzer — deterministic Python extractor + AI classification — stored in DB, exposed via two endpoints, displayed on ticket detail page, with zero impact on scheduling.

**Key architectural decisions grounded in the actual codebase:**

- **AI execution**: `execute_external_command` from `run_step.py` (already provider-agnostic) — no `anthropic`/`openai` imports. The analyzer owns its own 120-second subprocess timeout rather than modifying `run_step.py`.
- **Non-blocking POST**: `threading.Thread(target=_bg, daemon=True)` → HTTP 202, identical to `run-next` and `resolve-conflicts` in `routes/tickets.py`.
- **Database**: Extends `_SCHEMA` in both `runtime_db.py` (SQLite INSERT OR REPLACE) and `runtime_db_pg.py` (ON CONFLICT DO UPDATE).
- **Router**: New `services/control_api/routes/intelligence.py` with prefix `/tickets`; registered in `main.py` alongside existing routers.
- **Frontend**: New `TicketIntelligencePanel.jsx` uses the existing `usePolling` hook; wired into `TicketDetailPage.jsx`; `api/tickets.js` gets two new functions.
- **Missing from previous plan, now added**: explicit `api/tickets.js` client functions, explicit note that `exec_cmd` comes from `request.app.state.daemon_exec_cmd`, and clarification that `execute_external_command` is not modified.
