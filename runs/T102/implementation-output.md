All correct. The implementation is complete. Here's a summary:

---

## Changes made

**2 files created:**

- `services/control_api/services/board_service.py` — projects `runs/*/state.json` + `daemon.lock` + `retry-state.json` + `gh issue list` into 7 ordered columns (backlog → queued → running → waiting_human → blocked → pr_ready → done) with strict priority classification
- `apps/dashboard/src/pages/BoardPage.jsx` — kanban board UI with 7 columns, auto-polls every 10s, links ticket IDs to detail pages

**5 files modified:**

- `tools/agent_runner/run_daemon.py` — added `_sync_main_before_intake()` (checks for unknown dirty files, then `git checkout main` + `git pull origin main`), added `_count_active_tickets()`, rewrote `poll_github_issues()` to call sync first, check capacity, sort by issue number, intake at most 1, log others as queued/skipped-for-capacity; added `--max-active-tickets` CLI flag (default: 1)
- `services/control_api/models/schemas.py` — added `BoardItem`, `BoardColumn`, `BoardResponse` models
- `services/control_api/routes/daemon.py` — added `GET /daemon/board` endpoint
- `apps/dashboard/src/api/daemon.js` — added `getBoardData()`
- `apps/dashboard/src/App.jsx` — added `BoardPage` import, `/board` route, and "Board" nav link
