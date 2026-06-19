# Plan fix — dynamic AI documentation generation required

The current T196 plan is too limited because it instructs the LLM to emit exactly six fixed docs files.

That is not enough for real projects.

The AI analysis must detect the project structure, stack and features, then generate the documentation files that are actually needed.

## Required correction

Replace the fixed rule:

```text
emit exactly six files
```

with:

```text
emit the required base docs plus additional specialized docs based on repository analysis
```

## Repository analysis must detect

The AI analysis should inspect and infer as much as possible from:

```text
README*
package.json
pnpm-lock.yaml
yarn.lock
package-lock.json
pyproject.toml
requirements.txt
poetry.lock
Pipfile
pom.xml
build.gradle
gradle.properties
Dockerfile
docker-compose*.yml
Makefile
.github/workflows/
src/
app/
apps/
services/
packages/
libs/
tests/
config/
scripts/
migrations/
```

It should detect, when possible:

- project purpose
- languages
- frameworks
- package manager
- monorepo/workspace structure
- main entry points
- frontend/backend split
- services
- APIs/routes/controllers
- models/entities/domain objects
- database usage
- migrations
- authentication/security
- external integrations
- environment variables/config files
- Docker/deployment setup
- CI/CD workflows
- test strategy
- lint/typecheck/build commands
- validation commands
- risky areas
- unknowns requiring human review

## Required base docs

Always generate these files with non-empty project-specific content:

```text
docs/project-overview.md
docs/architecture.md
docs/local-development.md
docs/validation.md
docs/configuration.md
docs/dependencies.md
docs/testing-strategy.md
docs/deployment.md
docs/agent-guidelines.md
docs/known-risks-and-todos.md
```

## Conditional docs

Generate these only when relevant signals are detected:

```text
docs/api.md
docs/database.md
docs/frontend.md
docs/backend.md
docs/authentication.md
docs/ci-cd.md
docs/docker.md
docs/domain-model.md
docs/integrations.md
docs/monorepo.md
docs/scripts.md
docs/observability.md
docs/security.md
docs/data-flow.md
```

The LLM may also create additional `docs/*.md` files if the repository clearly needs them.

## Prompt builder changes

`docs_prompt_builder.py` must no longer hardcode exactly six file targets.

Instead, it must instruct the LLM to:

1. Analyze the repository.
2. Produce a short analysis summary.
3. Produce the base docs.
4. Produce additional specialized docs only when justified by detected evidence.
5. Mark uncertain findings as TODO instead of hallucinating.
6. Use the existing file block format:

```text
--- BEGIN FILE: docs/<name>.md ---
...
--- END FILE ---
```

## Install action changes

`install_agent_layout.py` must parse a variable number of generated docs files.

It must validate:

- all required base docs are present
- every generated file stays under `docs/`
- no absolute paths
- no path traversal
- files are non-empty

If conditional docs are generated, include them in the PR body summary.

## UI changes

The UI result card must not assume exactly six docs.

It should display:

- count of generated docs
- list of generated docs paths
- AI analysis summary
- warnings/TODOs
- PR URL

## Acceptance criteria additions

- The plan no longer says “exactly six files”.
- The AI docs generator creates base docs plus conditional docs depending on detected repository features.
- `docs/` is project-specific and not a fixed placeholder set.
- Generated docs paths are validated for safety.
- Tests cover variable doc generation, including at least one conditional doc such as `docs/api.md` or `docs/docker.md`.

## Review verdict

PLAN_FIX_REQUIRED until T196 plan includes dynamic AI docs generation instead of fixed six-file generation.
