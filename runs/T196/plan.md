## Objective

Add a UI action on the project detail page that installs or regenerates the standard AI Dev Factory agent layout (`ai/`, `docs/`, `prompts/`, `runs/`, `tickets/`) on any already-imported project, running an AI repository analysis to produce meaningful `docs/` content and opening a PR in the target repository.

## Included

### `tools/agent_runner/docs_prompt_builder.py` — new file
- Function `build_docs_prompt(project_root, file_tree)` that scans `README*`, `package.json`, `pyproject.toml`, `requirements.txt`, `pom.xml`, `build.gradle`, `Dockerfile`, `docker-compose*.yml`, `Makefile`, `src/`, `app/`, `services/`, `tests/` and produces a structured LLM prompt.
- Prompt instructs the LLM to emit exactly six files using the `--- BEGIN FILE: {path} --- ... --- END FILE ---` convention already used in `run_analysis.py`:
  - `docs/project-overview.md`
  - `docs/architecture.md`
  - `docs/local-development.md`
  - `docs/validation.md`
  - `docs/agent-guidelines.md`
  - `docs/known-risks-and-todos.md`

### `tools/agent_runner/install_agent_layout.py` — new file
- Function `install_agent_layout(project_path, project_id, exec_cmd)` orchestrating the full action:
  1. Detect if layout already exists → choose branch name (`ai-dev-factory/install-agent-layout` or `ai-dev-factory/update-agent-docs`) and PR title accordingly.
  2. Create/checkout the branch.
  3. Copy standard `ai/`, `prompts/generic/`, `runs/.gitkeep`, `tickets/.gitkeep` from the factory sources (reusing logic from `bootstrap_agent_layout.py`).
  4. Build file tree (reuse `run_analysis.py` helper).
  5. Call `docs_prompt_builder.build_docs_prompt()`, invoke the LLM via `exec_cmd`, parse `--- BEGIN FILE --- / --- END FILE ---` blocks, write files to `docs/`.
  6. Git-add, commit (`chore: add AI Dev Factory agent layout and generated docs`), push to origin.
  7. Create PR via `gh pr create` with body including: generated/updated folders, AI analysis summary, detected commands, TODOs requiring human review.
  8. Return `{"branch": …, "pr_url": …, "pr_number": …, "docs_summary": …, "warnings": […], "error": …}`.
- The function is idempotent: if layout folders already exist, it creates an update PR rather than overwriting.

### `services/supervisor/main.py`
- New endpoint `POST /projects/{project_id}/install-agent-layout`.
- Maps `project_id` to host path via `path_mapper`, resolves `exec_cmd` (same as used for analysis runs).
- Calls `install_agent_layout()` in a subprocess (or direct import, consistent with bootstrap pattern).
- Returns the result JSON.

### `services/control_api/routes/projects.py`
- New Pydantic model `InstallAgentLayoutResult` (branch, pr_url, pr_number, docs_summary, warnings, error).
- New endpoint `POST /projects/{project_id}/install-agent-layout`.
- Delegates to the supervisor endpoint for the given project.
- Returns `InstallAgentLayoutResult` to the frontend.

### `apps/dashboard/src/api/projects.js`
- New function `installAgentLayout(projectId)` → `POST /api/projects/{projectId}/install-agent-layout`.

### `apps/dashboard/src/pages/ProjectDashboardPage.jsx`
- Add a button labelled **"Install AI Dev Factory agent layout"** (or **"Regenerate agent layout / docs"** if layout already present, detected client-side from project metadata or toggled after first call).
- On click: call `installAgentLayout()`, show a loading/spinner state.
- On success: display a result card showing branch name, PR URL (clickable link), docs summary, and any warnings.
- On error: display the error message inline.
- No polling required; the action is synchronous from the UI perspective (blocking HTTP call with appropriate timeout).

### Tests
- `tests/test_docs_prompt_builder.py`: unit test verifying the prompt includes the expected file targets given a minimal file tree.
- `tests/test_install_agent_layout.py`: unit test mocking `subprocess` and `gh pr create`, verifying branch selection logic (install vs. update) and idempotency guard.

## Excluded

- Modifying the existing `bootstrap_agent_layout.py` (T195 path, new-project only).
- Changing the import/registration flow (`POST /projects/import`).
- Running the full ticket workflow state machine (planner/coder/reviewer) for this action.
- Auto-merging the generated PR.
- Any change to daemon lifecycle, sandbox validation, or auto-fix infrastructure.
- UI changes to pages other than `ProjectDashboardPage.jsx`.
- Regenerating `ai/` roles or skills if they already exist (docs/ update only on re-run).

## Acceptance criteria

- A button appears on the project detail page (`/projects/:projectId/dashboard`) for all registered projects.
- Clicking the button triggers `POST /api/projects/{projectId}/install-agent-layout` and shows a loading state.
- The action creates branch `ai-dev-factory/install-agent-layout` (or `ai-dev-factory/update-agent-docs` if layout exists) in the target repository.
- The branch contains all six `docs/` files with non-empty, project-specific content (not generic placeholders).
- The branch also contains `ai/`, `prompts/generic/`, `runs/.gitkeep`, `tickets/.gitkeep`.
- A PR is opened in the target repository; the PR body includes: list of generated folders, AI analysis summary, detected commands, and TODOs.
- The UI displays the PR URL as a clickable link, along with warnings and the docs summary.
- No commit is made directly to the default branch.
- Running the action a second time on a project where the layout already exists creates an update PR rather than failing or overwriting blindly.
- The action reuses the existing project registration (`project_runtime_root`) and does not re-run the full bootstrap sequence.
- `tests/test_docs_prompt_builder.py` and `tests/test_install_agent_layout.py` pass.
