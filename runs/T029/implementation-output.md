All 35 tests pass. Here's the summary of what was implemented:

## Files created — `apps/dashboard/`

**Config (6 files)**
- `package.json`, `vite.config.js`, `tailwind.config.js`, `postcss.config.js`, `index.html`, `src/index.css`

**API layer (2 files)** — all calls go through Vite proxy `/api` → `http://localhost:8080`
- `src/api/tickets.js` — 15 functions covering list, detail, logs, plan, review, tests, and all workflow/git actions
- `src/api/daemon.js` — status, start, stop, restart

**Components (2 files)**
- `src/components/ActionButton.jsx` — shows loading state, success/error message from API response
- `src/components/ErrorBanner.jsx` — dismissible alert with `role="alert"`

**Pages (3 files)**
- `src/pages/TicketsPage.jsx` — ticket table with state badges, links to detail
- `src/pages/TicketDetailPage.jsx` — tabbed view (overview/logs/plan/review/tests) + workflow panel + git panel, lazy-loads tab content
- `src/pages/DaemonPage.jsx` — status card (running/stopped, PID, uptime) + Start/Stop/Restart, auto-refreshes every 30s

**Tests (5 files)** — Vitest + React Testing Library
- `tests/api.test.js` — 17 tests (all endpoints + error propagation)
- `tests/TicketList.test.jsx` — 5 tests
- `tests/TicketDetail.test.jsx` — 7 tests
- `tests/DaemonPage.test.jsx` — 6 tests

Two corrections from the plan: proxy target is port **8080** (not 8000), and endpoints are kebab-case (`approve-plan`, `run-next`) matching the actual Control API.
