Now I have a clear picture. Let me write the plan.

---

## Objective

Correct the bootstrap flow so that importing a managed project creates the standard AI Dev Factory agent workspace (`ai/`, `docs/`, `prompts/`, `runs/`, `tickets/`) on a setup branch in the target project, and opens a PR proposing those changes. Remove any `.ai-dev-factory/` artefact left by the wrong T194 direction.

---

## Included

### 1. Remove wrong T194 artefact — `services/supervisor/main.py:1628–1639`
- Delete the block that writes `.ai-dev-factory/project.yml` into the target project path.

### 2. New module — `tools/agent_runner/bootstrap_agent_layout.py`
Create a focused module that:
- Accepts `project_path`, `project_id`, `project_name`, `repo_url`, `default_branch`, `validation_commands` as inputs.
- Creates branch `ai-dev-factory/bootstrap-agent-layout` in the target repo (via `git checkout -b` inside the project path; never commits to default branch).
- Generates the following folder tree with minimal, project-specific initial files:
  ```
  ai/
    roles/      (copy role stubs from the factory's own ai/roles/)
    skills/     (copy skill stubs from ai/skills/)
    templates/  (copy templates from ai/templates/)
  docs/
    ai/
      global-context.md   (project-specific header, rest is template)
  prompts/
    generic/              (copy generic fallback prompts)
  runs/                   (empty, .gitkeep)
  tickets/                (empty, .gitkeep)
  ```
- Substitutes project-specific values (project id, name, repo URL, default branch, validation commands) in generated files.
- Commits the generated tree with message `chore: add AI Dev Factory agent workspace`.
- Pushes the branch.
- Opens PR via `gh pr create` with title `Add AI Dev Factory agent workspace` and a body that explains the layout, which folders each agent step uses, detected validation commands, and any TODOs requiring human review.
- Returns `{ branch, pr_url, pr_number, error }`.

### 3. Extend supervisor bootstrap — `services/supervisor/main.py:bootstrap_project_host()`
- After the existing runtime directory creation, call the new `bootstrap_agent_layout` function.
- If the target path is a git repo with a GitHub remote: run full branch + commit + PR flow.
- If no GitHub remote: create branch and commit locally, set `pr_url=None`.
- If the layout already exists on any branch: skip and set `layout_skipped=True`.
- Capture errors without failing project registration (non-strict mode).

### 4. Update `BootstrapResult` model — locate where it is defined (control API models)
- Add fields: `agent_layout_branch: str | None`, `agent_layout_pr_url: str | None`, `agent_layout_pr_number: int | None`, `agent_layout_error: str | None`.

### 5. Propagate result through the control API — `services/control_api/services/project_bootstrap.py` and `services/control_api/routes/projects.py`
- Forward the new fields from supervisor response to the API response.
- Expose them in the `POST /projects/import` response body.

### 6. Agent runner project-local context loading — `tools/agent_runner/run_step.py`
- Verify (and if needed adjust) `compose_runtime_prompt()` so it prefers project-local `ai/`, `docs/`, `prompts/` when present, and gracefully falls back to factory defaults when those folders are absent. (The exploration shows loading is already path-relative; confirm no hardcoded factory-root assumptions break for external managed projects.)

### 7. Tests
- Unit test for `bootstrap_agent_layout.py`: verify folder structure generated, substitutions applied, branch/commit/PR calls made with correct args.
- Integration smoke test: bootstrap a tmp git repo, assert the five folders exist on the setup branch and the PR creation command was called with expected title/body.

---

## Excluded

- Generating ticket-specific prompt files (`prompts/Txx-*.md`) — those are created per-run by the workflow, not at bootstrap time.
- Modifying the runtime root structure (runs/, worktrees/, etc. managed by the factory itself) — that is already correct.
- Any UI changes beyond the API response fields that already exist.
- Migrating existing managed projects that were already bootstrapped — they keep working with defaults.
- Strict-mode enforcement (failing registration if PR creation fails) — out of scope per ticket.
- Modifying the `ai/`, `docs/`, `prompts/` content beyond what is needed for a minimal working agent workspace.

---

## Acceptance criteria

- `services/supervisor/main.py` no longer writes `.ai-dev-factory/project.yml` into the target project path.
- Bootstrapping a new project with a GitHub remote creates branch `ai-dev-factory/bootstrap-agent-layout` in the target repo containing `ai/`, `docs/`, `prompts/`, `runs/`, `tickets/`.
- The generated `docs/ai/global-context.md` contains the correct project id, name, and repo URL.
- A PR is opened on the target project with title `Add AI Dev Factory agent workspace`; the PR body lists all five folders and detected validation commands.
- Bootstrap never commits directly to the target default branch.
- `POST /projects/import` response includes `agent_layout_branch`, `agent_layout_pr_url`, and `agent_layout_pr_number`.
- If GitHub remote is unavailable, bootstrap still succeeds with `agent_layout_pr_url=null` and a local commit on the setup branch.
- If the agent workspace folders already exist in the target project, the bootstrap step is skipped without error.
- Existing managed projects without the layout continue to work with factory-level defaults (no regression in `run_step.py`).
- Unit tests for `bootstrap_agent_layout.py` pass.
