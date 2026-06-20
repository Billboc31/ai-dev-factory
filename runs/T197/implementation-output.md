All 34 tests pass. Here's a summary of the changes made:

**Files modified:**

1. **`services/control_api/routes/intelligence.py`** — added `project_router` with GET and POST handlers for `/projects/{project_id}/tickets/{ticket_id}/intelligence[/analyze]`; added idempotency guard in `analyze_intelligence` that returns 202 early if status is already `queued` or `running`.

2. **`services/control_api/main.py`** — registered `intelligence.project_router` after `intelligence.router`.

3. **`tools/agent_runner/ticket_intelligence_extractor.py`** — fixed `changes_scheduler` from set-intersection on split tokens to substring scan (`any(kw in lower for kw in _SCHEDULER_KEYWORDS)`), so composite identifiers like `scheduler_config` are correctly detected.

4. **`tests/test_ticket_intelligence_api.py`** — added 3 new tests: `test_project_get_intelligence_returns_analysis`, `test_project_post_analyze_returns_202` (project-scoped path coverage), and `test_post_analyze_idempotency_guard` (verifies no thread is launched when status is already running).
