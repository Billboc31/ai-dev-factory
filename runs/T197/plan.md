The plan has been written to `runs/T197/plan.md`. Here is a summary of what changed from the previous version and why:

**Fix 1 — Provider-agnostic AI execution**: Replaced the phrase "via existing Claude API integration pattern" with a concrete description of the existing `exec_cmd` subprocess abstraction. The analyzer builds a prompt file, runs `exec_cmd` (e.g., `claude`, a local Qwen CLI, or any other agent tool) as a subprocess, and captures stdout — no provider-specific SDK is imported. The `exec_cmd` value is injected from `app.state.daemon_exec_cmd` at call time, the same way the daemon already works.

**Fix 2 — Non-blocking POST analyze**: Changed the endpoint from a synchronous blocking AI call to a `202 Accepted` response backed by FastAPI `BackgroundTasks`. The HTTP response returns immediately with `{"ticket_id": ..., "analysis_status": "queued"}`. The background task transitions status `queued → running → completed` (or `failed`), with an explicit subprocess timeout stored as `analysis_status = failed` + `last_error` on timeout or exception.

**Fix 3 — Analysis status lifecycle**: The DB and API now support all five states: `not_started`, `queued`, `running`, `completed`, `failed`.

**Fix 4 — UI states**: `TicketIntelligencePanel` now explicitly handles no-analysis, queued/running (spinner + slow polling), completed, and failed states. The advisory badge is always visible regardless of state.
