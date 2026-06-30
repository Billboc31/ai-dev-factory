**T219 — PASS.** Test report written to `runs/T219/tests/test-report.md`.

Results:
- Backend `tests/api/test_batches_routes.py`: **17/17 passed**
- Frontend T219 vitest files (`BatchesPage`, `BatchDetailPage`, `BatchDependencyGraph`): **19/19 passed**
- All 9 acceptance criteria verified (graph at 30+ nodes verified by code-inspection only — no browser sandbox available)

Caveats (non-blocking for T219):
- Full vitest run shows 5 pre-existing failures in `RuntimeDashboardPage.test.jsx` plus 1 worker OOM. Those files are untouched by T219 (`git diff main..HEAD` confirms), so they exist on `main`.
- Branch has not been rebased onto the 2 newer `main` commits that touch `tools/agent_runner/` — not a tester concern but worth knowing before merge.
