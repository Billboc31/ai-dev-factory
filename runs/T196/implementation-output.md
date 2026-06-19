All changes are in place. Here's a summary of everything implemented:

## Summary

All 8 deliverables from the approved plan are complete. 28 new tests pass, 0 regressions.

### Files created
- **`tools/agent_runner/docs_prompt_builder.py`** — Scans the repo (README, package.json, pyproject.toml, Dockerfile, docker-compose, Makefile, source directories, etc.) and builds the LLM prompt instructing Claude to produce 10 required base docs plus up to 14 conditional docs based on detected signals.
- **`tools/agent_runner/install_agent_layout.py`** — Orchestrator: calls the LLM, parses variable-number FILE blocks, validates every path (no absolute, no traversal, must be under `docs/`, must be `.md`), checks all 10 base docs are present, ensures `ai/prompts/runs/tickets/` layout dirs exist (idempotent), commits to `ai-dev-factory/install-agent-layout` (new) or `ai-dev-factory/update-agent-docs` (existing), pushes and creates/reuses a PR.
- **`tests/test_install_agent_layout.py`** — 28 tests covering: variable doc generation, conditional docs (`docs/docker.md`, `docs/api.md`), path validation rejection (absolute, traversal, non-markdown), missing base docs warning, idempotency, LLM failure, branch selection (install vs update).

### Files modified
- **`services/control_api/models/schemas.py`** — Added `InstallAgentLayoutResult` with `docs_paths: list[str]`, `docs_count: int`, `analysis_summary`, `warnings`, `error`.
- **`services/supervisor/main.py`** — Added `POST /projects/{project_id}/install-agent-layout` endpoint (synchronous, delegates to `install_agent_layout()`).
- **`services/control_api/routes/projects.py`** — Added `POST /{project_id}/install-agent-layout` endpoint proxying to supervisor with 420s timeout.
- **`apps/dashboard/src/api/projects.js`** — Added `installAgentLayout(projectId)` with 420s timeout.
- **`apps/dashboard/src/pages/ProjectDashboardPage.jsx`** — Added "Install agent layout" ActionButton and result card showing PR URL, branch, analysis summary, generated doc count/list, and warnings.
