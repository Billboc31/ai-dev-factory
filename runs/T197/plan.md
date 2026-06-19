The plan is complete and properly structured. Here's a summary of what it covers:

**Objective**: Advisory Ticket Intelligence Analyzer — pre-dev, informational only, no scheduler impact.

**Key design decisions** (addressing the review blockers):

1. **Provider-agnostic AI**: Uses `execute_external_command(exec_cmd, prompt)` from `run_step.py` — same subprocess pattern as `resolve-conflicts`. No `anthropic`/`openai` imports. Model catalog uses logical names (`advanced-reasoning-model`, etc.).

2. **Non-blocking POST**: Returns HTTP 202 immediately with `{"analysis_status": "queued"}`. Analysis runs in `threading.Thread(target=_bg, daemon=True)` — identical to the `run-next` and `resolve-conflicts` patterns.

3. **Explicit timeout**: 120-second `subprocess.run(timeout=120)` wrapping the AI call; `TimeoutExpired` persists `analysis_status = "failed"`.

4. **Five-state lifecycle**: `not_started → queued → running → completed → failed` in a new `ticket_intelligence` SQLite/Postgres table (added via `CREATE TABLE IF NOT EXISTS`, no migration framework needed).

5. **Hybrid analysis**: `compute_signals()` is pure Python (risky keywords, domain detection, dependency refs, token estimate) — runs before the AI prompt is built.

6. **UI**: New `TicketIntelligencePanel.jsx` handles all states with polling, advisory badge always visible, wired into `TicketDetailPage.jsx`.
