The revised plan has been written to `runs/T196/plan.md`. Here is a summary of the key changes from the previous version:

**What changed:**

- **`docs_prompt_builder.py`** no longer hardcodes "exactly six files." It now instructs the LLM to produce 10 required base docs (`project-overview`, `architecture`, `local-development`, `validation`, `configuration`, `dependencies`, `testing-strategy`, `deployment`, `agent-guidelines`, `known-risks-and-todos`) plus up to 14 conditional docs driven by detected signals (Docker, API routes, database migrations, CI/CD, etc.).

- **Repository scan** is expanded to include `pnpm-lock.yaml`, `poetry.lock`, `gradle.properties`, `apps/`, `packages/`, `libs/`, `config/`, `scripts/`, `migrations/`, `.github/workflows/` — covering monorepos, Python, JVM, and Node.js project shapes.

- **`install_agent_layout.py`** now parses a variable number of FILE blocks, validates every generated path (no absolute paths, no traversal, must stay under `docs/`, must be non-empty), checks all 10 base docs are present, and returns `docs_paths` + `docs_count` instead of assuming a fixed count.

- **`InstallAgentLayoutResult`** model gains `docs_paths: list[str]` and `docs_count: int`.

- **UI result card** shows the actual generated doc count and path list, not a hardcoded "6 files."

- **Tests** cover variable doc generation and verify at least two conditional docs (`docs/docker.md`, `docs/api.md`) and path validation rejection.
