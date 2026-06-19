The plan has been written to `runs/T197/plan.md`. Here's what it covers:

**Objective**: Advisory Ticket Intelligence Analyzer — pre-dev, informational only, no scheduler impact.

**Key design decisions addressing the two review blockers:**

1. **Provider-agnostic AI**: Uses `execute_external_command(exec_cmd, prompt)` from `run_step.py` (same subprocess pattern as `resolve-conflicts`). No `anthropic`/`openai` imports anywhere. Model catalog uses only logical names (`balanced-code-model`, `advanced-reasoning-model`, etc.) — provider mapping stays in environment config.

2. **Non-blocking POST (202)**: `POST /tickets/{ticket_id}/intelligence/analyze` returns `{"analysis_status": "queued"}` immediately via `threading.Thread(target=_bg, daemon=True)` — identical to the `run-next` and `resolve-conflicts` patterns already in `routes/tickets.py`.

3. **Explicit timeout + failure persistence**: `subprocess.run(timeout=120)` in `run_ticket_intelligence.py`; `TimeoutExpired` persists `analysis_status = failed`.

4. **Five-state lifecycle**: `not_started → queued → running → completed → failed` in a new `ticket_intelligence` table added via `CREATE TABLE IF NOT EXISTS` in both `runtime_db.py` and `runtime_db_pg.py`.

5. **Hybrid analysis**: `compute_signals()` is pure Python (keywords, domains, dependency refs, token estimate) — tested in isolation, embedded in the AI prompt.

6. **UI**: New `TicketIntelligencePanel.jsx` handles all states with polling, advisory badge always visible, wired into `TicketDetailPage.jsx`.
