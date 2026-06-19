# Plan review — dynamic AI documentation generation required

The current T196 plan is directionally correct for the UI action and project reuse, but it is too limited for the documentation generation part.

## Blocking concern

The plan says the LLM should emit exactly six fixed files:

```text
docs/project-overview.md
docs/architecture.md
docs/local-development.md
docs/validation.md
docs/agent-guidelines.md
docs/known-risks-and-todos.md
```

That is not enough.

The user requirement is that the AI analysis detects as much as possible about the project and generates the docs the project actually needs.

## Required correction

Replace the fixed six-file generation with dynamic documentation generation:

- always generate a required base documentation set
- generate additional specialized docs depending on detected project features
- allow the AI to create additional `docs/*.md` files when justified by repository evidence
- validate generated paths and reject unsafe paths

## Repository analysis must detect

At minimum, inspect and infer from:

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

The analysis should detect:

- project purpose
- languages/frameworks
- package manager
- monorepo/workspace structure
- entry points
- frontend/backend split
- APIs/routes/controllers
- models/entities/domain objects
- database/migrations
- authentication/security
- integrations
- environment variables/configuration
- Docker/deployment
- CI/CD
- tests/lint/typecheck/build/validation commands
- risks and unknowns

## Required base docs

Always generate these with non-empty project-specific content:

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

Generate these when relevant signals are detected:

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

## Acceptance additions

- The plan no longer says “exactly six files”.
- `docs_prompt_builder.py` asks for base docs plus conditional docs.
- `install_agent_layout.py` parses a variable number of generated docs files.
- Generated docs paths must stay under `docs/`, with no absolute paths or traversal.
- UI displays generated doc count and doc paths instead of assuming six files.
- Tests cover variable docs and at least one conditional doc.

## Review verdict

PLAN_FIX_REQUIRED until the plan includes dynamic AI docs generation instead of a fixed six-file output.
