I have a clear picture of the codebase. Here is the implementation plan:

---

## Objective

Extend project bootstrap to generate a complete set of agent onboarding files (`.ai-dev-factory/`) inside the target repository on a dedicated branch, attempt to open a GitHub setup PR, and make all agent steps load project-local context files when present. Existing projects without onboarding continue to work unchanged.

---

## Included

### A. Stack detection and onboarding file generation — `services/supervisor/main.py`

- Replace `_detect_stack_for_path` with a new `_detect_stack_info(project_root: Path) -> dict` that returns both the stack label and a dict of detected commands (install, test, lint, build, run). Detection rules:
  - `pyproject.toml` / `requirements.txt` → stack `python`, test `pytest`, lint `ruff check .`, typecheck `mypy .` (each only if config file confirms the tool, otherwise `# TODO: add command`)
  - `package.json` → stack `node`, scripts parsed from `package.json` (`npm test`, `npm run build`, etc.)
  - `pom.xml` → stack `java`, test `mvn test`
  - `build.gradle` → stack `java`, test `./gradlew test`
  - `go.mod` → stack `go`, test `go test ./...`
  - `Cargo.toml` → stack `rust`, test `cargo test`
  - `Makefile` → supplement any stack with make targets if parseable
  - Undetected commands emit a `# TODO: …` placeholder rather than a guess.

- In `bootstrap_project_host`, after creating the runtime dirs, call `_generate_onboarding_files(project_root, project_id, stack_info)` which creates the following files inside `.ai-dev-factory/` **only if each file does not already exist** (idempotent per-file, so re-bootstrap never overwrites customised files):

  | File | Content |
  |---|---|
  | `project.yml` | already created; extend to include detected commands block and `default_branch` |
  | `agent-context.md` | Template: project name, detected stack, directory tour placeholder, known constraints, areas to avoid |
  | `commands.md` | Detected install/run/test/lint/build/validate commands with TODO placeholders |
  | `validation.yml` | Ordered YAML steps derived from detected test/lint/typecheck commands |
  | `conventions.md` | Default coding conventions (formatting, naming, branch naming, PR style) |
  | `run-ticket-prompt.md` | Project-specific guidance injected into every run-ticket step |
  | `planning-prompt.md` | Project-specific planning context fragment |
  | `implementation-prompt.md` | Project-specific implementation context fragment |
  | `review-prompt.md` | Project-specific review context fragment |
  | `test-prompt.md` | Project-specific test context fragment |
  | `safety.md` | Safety guardrails (no secrets, no unrelated file edits, no history rewrites, no destructive commands) |

  Return a list of `created_files` (new) and `skipped_files` (already existed) to build `onboarding_warnings`.

### B. Branch creation and commit — `services/supervisor/main.py`

- After generating files, if any files were created, `_commit_onboarding(project_root, created_files) -> tuple[str, str | None]` runs:
  1. `git symbolic-ref --short HEAD` to capture the current branch.
  2. Check whether `ai-dev-factory/bootstrap-agent-setup` already exists; if so, use `ai-dev-factory/bootstrap-agent-setup-{YYYYMMDD}` to avoid conflict.
  3. `git checkout -b <branch>` from HEAD.
  4. `git add .ai-dev-factory/`.
  5. `git commit -m "chore: add AI Dev Factory agent onboarding files"`.
  6. Return `(branch_name, None)` on success or `(branch_name, error_message)` on failure.
  7. On any git error, restore the original branch and surface the error as a warning (non-fatal).

### C. PR creation — `services/supervisor/main.py`

- `_open_setup_pr(project_root, branch_name, stack_info, created_files, warnings) -> str | None` runs:
  1. Check for `git remote get-url origin` — if none, return None immediately.
  2. Push branch to origin (`git push -u origin <branch>`).
  3. Invoke `gh pr create --title "Add AI Dev Factory agent onboarding files" --body "..."` with a body listing generated files, detected stack, TODOs, and instructions for customisation.
  4. Return the PR URL from stdout on success, None on any error (gh not found, not authenticated, no remote).
  5. All failures are non-fatal and surface as entries in `onboarding_warnings`.

- Add all three new fields to the supervisor's response JSON: `onboarding_branch`, `onboarding_pr_url`, `onboarding_warnings`.

### D. Schema extensions

- **`services/control_api/models/schemas.py`** — `BootstrapResult`:
  ```python
  onboarding_branch: str | None = None
  onboarding_pr_url: str | None = None
  onboarding_warnings: list[str] = []
  ```
- **`services/control_api/models/schemas.py`** — `ProjectInfo`:
  ```python
  onboarding_exists: bool = False
  ```
- **`services/control_api/services/project_bootstrap.py`** — `BootstrapResult` dataclass: add the same three fields; `bootstrap()` propagates them from the supervisor response dict via `data.get(...)`.

### E. Agent step context injection — `tools/agent_runner/run_step.py`

- Add a constant `STEP_PROJECT_CONTEXT_FILES: dict[str, list[str]]`:
  ```python
  {
      "planner":        ["run-ticket-prompt.md", "planning-prompt.md", "agent-context.md"],
      "coder":          ["run-ticket-prompt.md", "implementation-prompt.md", "conventions.md"],
      "review":         ["run-ticket-prompt.md", "review-prompt.md", "safety.md"],
      "tester":         ["run-ticket-prompt.md", "test-prompt.md", "validation.yml"],
      "memory-updater": ["run-ticket-prompt.md"],
      "conflict-resolver": ["run-ticket-prompt.md", "safety.md"],
  }
  ```
- In `compose_runtime_prompt`, after injecting global context/role/skills and before the TASK section, loop over `STEP_PROJECT_CONTEXT_FILES.get(step, [])`. For each filename, check `Path(".ai-dev-factory") / filename`; if it exists, append it as a labeled section `# PROJECT CONTEXT: {filename}`. Missing files are silently skipped (`_log_runtime` records the skip).

### F. Project list API enrichment — `services/control_api/routes/projects.py`

- Add a helper `_onboarding_exists(project_root: Path) -> bool` that returns `True` when `project_root / ".ai-dev-factory" / "agent-context.md"` exists (more than just `project.yml` which is created at minimal bootstrap).
- In `list_projects`, populate `onboarding_exists` when enriching each `ProjectInfo`.

### G. UI — project import result and project list

- Identify the frontend component that renders the import/bootstrap API response (look in `services/web/` or similar) and add display of `onboarding_branch`, `onboarding_pr_url` (as a clickable link), and `onboarding_warnings`.
- In the project list component, add an indicator (icon or badge) when `onboarding_exists` is `true`.
- (Frontend component paths to be confirmed by the coder — search for the component rendering `BootstrapResult` or the project import form.)

---

## Excluded

- Stack detection for ecosystems beyond Python, Node, Go, Rust, Java/Maven, Java/Gradle (e.g., Ruby, PHP, .NET) — a follow-up ticket can extend detection.
- Automatic merging of the onboarding PR.
- UI action to regenerate/update onboarding from the project detail page — noted as desired behavior but deferred.
- Validating that detected commands actually execute successfully during bootstrap.
- Replacing all built-in prompts with project-local equivalents in one pass.

---

## Acceptance criteria

1. `POST /projects/import` on a Python project with `pyproject.toml` creates all 10 onboarding files in `.ai-dev-factory/` inside the target repo.
2. `commands.md` and `validation.yml` contain `pytest` (detected) and at least one `# TODO` placeholder for an undetected command.
3. The default branch of the target project is unmodified; onboarding files are committed on branch `ai-dev-factory/bootstrap-agent-setup`.
4. `BootstrapResult` includes `onboarding_branch` (non-null), `onboarding_pr_url` (null if PR creation fails), and `onboarding_warnings` (list, may be empty).
5. Re-importing an already-bootstrapped project does not overwrite existing `.ai-dev-factory/` files and does not raise an error.
6. When `.ai-dev-factory/planning-prompt.md` exists in the worktree, `compose_runtime_prompt` for step `planner` includes a `# PROJECT CONTEXT: planning-prompt.md` section in the composed prompt.
7. When `.ai-dev-factory/` is absent, all agent steps (planner, coder, review, tester) produce identical prompts to today — no regression.
8. `GET /projects` returns `onboarding_exists: true` for bootstrapped projects and `false` for projects that have only a minimal `project.yml`.
9. The project import result UI displays the branch name and, when available, a link to the PR.
