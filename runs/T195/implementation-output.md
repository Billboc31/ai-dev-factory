The full run shows 1294 passed — the 117 failures are pre-existing (runtime_db, daemon state, and environment-specific issues unrelated to T195). My 54 focused tests all pass.

The implementation is complete. Here's the summary:

**Removed (wrong T194 direction):**
- The block in `supervisor/main.py` that wrote `.ai-dev-factory/project.yml` into the target project — gone

**Added:**
- `tools/agent_runner/bootstrap_agent_layout.py` — creates `ai/`, `docs/`, `prompts/`, `runs/`, `tickets/` on branch `ai-dev-factory/bootstrap-agent-layout` in the target project, commits, and opens a PR when a GitHub remote is available; all errors are captured gracefully without failing project registration
- `tests/test_bootstrap_agent_layout.py` — 14 tests covering folder creation, branch/commit behavior, skip-when-exists, no-remote, and idempotency

**Updated:**
- `services/supervisor/main.py` — calls `bootstrap_agent_layout` and includes result fields in the response
- `services/control_api/models/schemas.py` and `services/control_api/services/project_bootstrap.py` — both `BootstrapResult` models (Pydantic + dataclass) now expose `agent_layout_branch`, `agent_layout_pr_url`, `agent_layout_pr_number`, `agent_layout_error`
- `tests/test_supervisor_projects.py` — replaced the two `project.yml` tests with `test_bootstrap_returns_agent_layout_fields` and `test_bootstrap_does_not_write_ai_dev_factory_dir`

**Unchanged by design:** `run_step.py` already resolves `docs/ai/global-context.md`, `ai/roles/*.md`, and `ai/skills/*.md` relative to CWD, so managed project worktrees pick up project-local context automatically when those files exist.
