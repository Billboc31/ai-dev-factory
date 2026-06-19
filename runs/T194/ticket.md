# T194 — T194 - Project bootstrap must inject agent onboarding files and propose a setup PR

**Source**: GitHub Issue #241

## Description

# Objective

Current project bootstrap mostly creates runtime infrastructure:

```text
clones/
worktrees/
runs/
logs/
state/
```

That is not enough for a managed project to be immediately codable by agents.

Bootstrap must also onboard the target repository by injecting the files, prompts, commands, and validation contract required by AI Dev Factory agents.

---

# Problem

After importing/bootstraping a new project, the agent runtime knows where the project is, but the project itself does not contain enough context for agents to work safely and consistently.

Missing examples:

- project-specific agent context
- run-ticket prompt contract
- validation commands
- coding conventions
- test/build commands
- repository architecture notes
- agent safety boundaries
- PR/branch conventions
- generated onboarding PR

Without this, agents may code blindly or require manual setup per project.

---

# Expected behavior

Project bootstrap should include a new **Project Agent Setup** phase.

When importing a project, the system should:

1. Validate/register the project.
2. Create the project runtime root.
3. Detect the project stack as much as possible.
4. Generate agent onboarding files inside the target repository.
5. Create a dedicated setup branch.
6. Commit the generated onboarding files.
7. Open a PR on the target project proposing the AI Dev Factory setup.
8. Keep the project usable even if PR creation fails, with a clear error/status.

---

# Files to generate in the target repository

Create a project-local folder:

```text
.ai-dev-factory/
```

Suggested contents:

```text
.ai-dev-factory/
├── project.yml
├── agent-context.md
├── commands.md
├── validation.yml
├── conventions.md
├── run-ticket-prompt.md
├── planning-prompt.md
├── implementation-prompt.md
├── review-prompt.md
├── test-prompt.md
└── safety.md
```

Exact filenames can evolve, but the bootstrap must cover the same responsibilities.

---

# Required file responsibilities

## project.yml

Machine-readable project configuration.

Should include:

- project id
- project name
- repository path/url if known
- default branch
- detected language/framework
- package manager
- runtime hints
- validation command references
- agent capabilities enabled for this project

## agent-context.md

Human-readable project context for agents.

Should include:

- what the project does
- high-level architecture
- important directories
- known constraints
- areas agents should avoid
- preferred style of changes

## commands.md

Commands agents and humans can run.

Examples:

- install dependencies
- run app
- run tests
- run lint
- run typecheck
- run build
- run local validation

## validation.yml

Machine-readable validation contract.

Should include ordered validation steps such as:

```yaml
steps:
  - name: tests
    command: pytest
  - name: lint
    command: ruff check .
```

Commands should be generated from detection when possible and editable afterward.

## conventions.md

Project coding conventions.

Should include detected or default conventions:

- formatting
- naming
- API style
- test style
- branch naming
- PR expectations

## run-ticket-prompt.md

Project-specific prompt/context injected into run-ticket execution.

Should explain:

- how an agent should approach a ticket in this project
- how to inspect context
- how to make minimal safe changes
- how to update tests
- how to report validation results

## planning/implementation/review/test prompts

Prompt fragments used by the local agent pipeline.

These should make the agent workflow project-aware without hardcoding everything inside AI Dev Factory itself.

## safety.md

Project-specific safety and guardrails.

Should include:

- never commit secrets
- never modify unrelated files
- never rewrite history unless requested
- do not run destructive commands
- ask for human gate where required

---

# Stack detection

Bootstrap should inspect the project and infer sensible defaults from files like:

```text
package.json
pnpm-lock.yaml
yarn.lock
requirements.txt
pyproject.toml
pom.xml
build.gradle
docker-compose.yml
Dockerfile
Makefile
```

Examples:

- Node project → install/test/build commands from package scripts.
- Python project → pytest/ruff/mypy if detected.
- Java/Maven project → `mvn test` or existing wrapper.
- Docker project → compose commands if present.

If detection is uncertain, generate TODO placeholders rather than guessing dangerously.

---

# PR behavior

Bootstrap must not directly modify the target default branch.

It should create a branch such as:

```text
ai-dev-factory/bootstrap-agent-setup
```

Then commit generated files and open a PR:

```text
Add AI Dev Factory agent onboarding files
```

The PR body should explain:

- what was generated
- how to customize it
- how agents will use it
- what commands were detected
- any TODOs requiring human review

If the target repository has no GitHub remote or PR creation fails:

- keep the branch/commit locally if possible
- expose the failure clearly in bootstrap result and UI
- do not fail the whole project registration unless the user requested strict mode

---

# Integration with agent runtime

After the onboarding files exist, run-ticket / planner / coder / reviewer / tester should load the project-local context when present.

Expected lookup:

```text
<project_root>/.ai-dev-factory/
```

Agent steps should include relevant files in their context/prompt.

At minimum:

- run-ticket loads `run-ticket-prompt.md`
- planner loads `planning-prompt.md` + `agent-context.md`
- implementation loads `implementation-prompt.md` + `conventions.md`
- review loads `review-prompt.md` + `safety.md`
- test step loads `test-prompt.md` + `validation.yml`

---

# UI expectations

Project import/bootstrap result should show:

- runtime created
- agent onboarding generated
- branch name
- PR URL if created
- warnings/TODOs from stack detection

Project detail page should expose:

- whether onboarding exists
- link/open action for `.ai-dev-factory` files
- ability to regenerate/update onboarding later if needed

---

# Acceptance criteria

- Bootstrapping a new project creates `.ai-dev-factory/*` onboarding files on a setup branch.
- Bootstrap opens a PR proposing those files when a GitHub remote is available.
- Bootstrap never commits directly to the target default branch.
- Generated validation commands are based on detected project files when possible.
- Uncertain commands are marked as TODO instead of guessed silently.
- run-ticket/planner/implementation/review/test steps load project-local prompt/context files when present.
- Project import UI displays onboarding/PR status.
- Existing projects without `.ai-dev-factory` continue to work with defaults.
- Regenerating onboarding is idempotent or clearly creates an update PR.

---

# Non-goals

- Fully solving stack detection for every ecosystem in one pass.
- Replacing all built-in prompts immediately.
- Automatically merging the onboarding PR.
