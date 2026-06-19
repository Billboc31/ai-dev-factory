The plan has been written to `runs/T197/plan.md`. Here is a summary:

**Objective**: Add an advisory Ticket Intelligence Analyzer — pre-development, advisory only, no scheduler impact.

**Key design decisions from the retry context:**

1. **Provider-agnostic AI execution**: The analyzer invokes `exec_cmd` (from `app.state.daemon_exec_cmd`) as a subprocess, identical to the existing `resolve-conflicts` pattern. No provider-specific SDK is imported.

2. **Non-blocking POST analyze**: Returns HTTP 202 immediately with `{"ticket_id": ..., "analysis_status": "queued"}`. Analysis runs in a `threading.Thread` (consistent with `run-next` and `resolve-conflicts` patterns already in the codebase).

3. **Five-state lifecycle**: `not_started → queued → running → completed → failed`, persisted in the new `ticket_intelligence` SQLite table.

4. **Hybrid analysis**: A pure-Python `compute_signals()` function extracts deterministic features (risky keywords, domain tags, dependency references, token size estimate, migration/scheduler flags) before the AI prompt is built — no AI for those signals.

5. **UI handles all states**: `TicketIntelligencePanel` renders spinner+polling for queued/running, full table for completed, error+retry for failed, with the advisory badge always visible.
