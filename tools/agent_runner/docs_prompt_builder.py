"""Build the LLM prompt for AI-assisted agent layout documentation generation.

Pure string construction — no I/O, no LLM dependency.
"""
from __future__ import annotations

import os
from pathlib import Path

_SCAN_FILES = [
    "README.md", "README.rst", "README",
    "package.json", "pnpm-lock.yaml", "yarn.lock", "package-lock.json",
    "pyproject.toml", "requirements.txt", "poetry.lock", "Pipfile",
    "pom.xml", "build.gradle", "gradle.properties",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml",
    ".env.example", ".env.sample",
    "go.mod",
    "Cargo.toml",
]

_SCAN_DIRS = [
    "src", "app", "apps", "services", "packages", "libs",
    "config", "scripts", "migrations", "tests", ".github/workflows",
]

_REQUIRED_BASE_DOCS = [
    "docs/project-overview.md",
    "docs/architecture.md",
    "docs/local-development.md",
    "docs/validation.md",
    "docs/configuration.md",
    "docs/dependencies.md",
    "docs/testing-strategy.md",
    "docs/deployment.md",
    "docs/agent-guidelines.md",
    "docs/known-risks-and-todos.md",
]

_CONDITIONAL_DOCS = [
    "docs/api.md",
    "docs/database.md",
    "docs/frontend.md",
    "docs/backend.md",
    "docs/authentication.md",
    "docs/ci-cd.md",
    "docs/docker.md",
    "docs/domain-model.md",
    "docs/integrations.md",
    "docs/monorepo.md",
    "docs/scripts.md",
    "docs/observability.md",
    "docs/security.md",
    "docs/data-flow.md",
]

_SKIP_DIRS = frozenset({
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", ".tox", "dist", "build",
})

_INSTRUCTIONS_TEMPLATE = """\
You are an expert software architect. Analyze the repository described below and \
generate comprehensive AI agent documentation for the `docs/` folder.

## Instructions

1. Analyze the repository evidence provided (file contents and tree).
2. Write a short analysis summary (2-5 sentences) of the project.
3. Generate ALL required base documentation files listed below.
4. (Re)generate the project memory file `docs/ai/global-context.md` — see the \
dedicated section. ALWAYS generate it.
5. Generate ONLY the conditional documentation files for which you found clear \
evidence in the repository (do not generate files for features not present).
6. Mark any uncertain findings with "TODO: verify" rather than guessing.
7. Use only information you can infer from the provided repository evidence.

## Output format

Output ONLY file blocks in this exact format — no text outside the blocks:

--- BEGIN FILE: docs/<name>.md ---
<Markdown content>
--- END FILE ---

--- BEGIN FILE: docs/ai/global-context.md ---
<project memory — see structure below>
--- END FILE ---

--- BEGIN FILE: docs/analysis-summary.md ---
<2-5 sentence project analysis summary>
--- END FILE ---

## Project memory — `docs/ai/global-context.md` (ALWAYS generate)

This file is the canonical project memory injected at the top of EVERY AI agent \
prompt (planner/coder/reviewer/tester). Make it as complete as the evidence \
allows — it is the single most important file for agents to behave well on this \
project. It will be kept up to date by the memory-updater as development \
progresses, so write it as a living document.

Keep it concise and strictly evidence-based. If the repository is nearly empty, \
produce a short but well-structured skeleton with `TODO:` placeholders rather \
than inventing content.

IMPORTANT — preserve accumulated memory: if `docs/ai/global-context.md` already \
exists in the repository, treat it as authoritative project memory. Preserve all \
existing content, only refine wording and append newly-evidenced facts; never \
delete history or accumulated decisions. If it does not exist, create it fresh.

Use exactly these sections:

```
# Global Context — <Project Name>

## Identity
- project_id, repository, primary language/stack

## Purpose
What the project does and who/what it serves.

## Stack & Components
Languages, frameworks, runtime services, key directories.

## Architecture
High-level structure, main modules, how they interact.

## Conventions & Invariants
Coding conventions, naming, things that must always hold true.

## Workflow notes
Build/test/run commands, branching, anything an agent must know before acting.

## Known risks & TODOs
Gaps, uncertainties, follow-ups (use `TODO:` for unverified items).
```

## Required base docs (ALWAYS generate these 10 files)

{required_docs}

## Conditional docs (generate ONLY when evidence is present)

{conditional_docs}

## Doc content guidance

**docs/project-overview.md** — what the project does, detected stack, main runtime components
**docs/architecture.md** — high-level architecture, main modules/directories, data/control flow when inferable
**docs/local-development.md** — install commands, run commands, useful local URLs if detected
**docs/validation.md** — test/lint/build/typecheck commands, confidence level, TODOs where uncertain
**docs/configuration.md** — environment variables, config files, required secrets
**docs/dependencies.md** — key runtime dependencies, package manager, lock file status
**docs/testing-strategy.md** — test framework, test locations, coverage expectations
**docs/deployment.md** — how to build, how to deploy, infrastructure notes
**docs/agent-guidelines.md** — how AI agents should work in this repo, conventions, safe-change policy, files to avoid
**docs/known-risks-and-todos.md** — uncertain detections, missing tests, missing docs, commands requiring human confirmation
**docs/ai/global-context.md** — canonical project memory injected into every agent prompt (see the dedicated section above for the required structure)

**docs/api.md** — API routes, endpoints, request/response shape (generate if routes/controllers found)
**docs/database.md** — database type, schema, migrations (generate if DB detected)
**docs/frontend.md** — frontend stack, build, assets (generate if frontend detected)
**docs/backend.md** — backend services, entry points (generate if complex backend detected)
**docs/authentication.md** — auth strategy, tokens, sessions (generate if auth detected)
**docs/ci-cd.md** — CI/CD workflows, checks, deployment pipeline (generate if .github/workflows found)
**docs/docker.md** — Docker setup, services, compose configuration (generate if Docker found)
**docs/domain-model.md** — entities, domain objects, data model (generate if models detected)
**docs/integrations.md** — external APIs, services, webhooks (generate if integrations found)
**docs/monorepo.md** — workspace structure, packages, shared libs (generate if monorepo detected)
**docs/scripts.md** — utility scripts, automation (generate if scripts/ found)
**docs/observability.md** — logging, monitoring, metrics (generate if observability tools detected)
**docs/security.md** — security configuration, secrets management (generate if security concerns found)
**docs/data-flow.md** — data flow between components (generate if complex data flow detected)

## Repository evidence

### File tree

{file_tree}

### Scanned file contents

{file_contents}
"""


def _build_file_tree(root: Path, max_depth: int = 4) -> str:
    lines: list[str] = [root.name + "/"]

    def _walk(path: Path, depth: int, prefix: str) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name))
        except PermissionError:
            return
        for i, entry in enumerate(entries):
            if entry.name in _SKIP_DIRS:
                continue
            is_last = i == len(entries) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if is_last else "│   "
                _walk(entry, depth + 1, prefix + extension)

    _walk(root, 1, "")
    return "\n".join(lines)


def _read_file_capped(path: Path, max_bytes: int = 4096) -> str:
    try:
        raw = path.read_bytes()
        text = raw[:max_bytes].decode("utf-8", errors="replace")
        if len(raw) > max_bytes:
            text += f"\n... (truncated at {max_bytes} bytes)"
        return text
    except OSError:
        return ""


def _scan_directory_listing(path: Path, max_entries: int = 30) -> str:
    try:
        entries = sorted(path.iterdir(), key=lambda e: (e.is_file(), e.name))
    except (PermissionError, OSError):
        return ""
    lines = []
    for e in entries[:max_entries]:
        if e.name in _SKIP_DIRS:
            continue
        suffix = "/" if e.is_dir() else ""
        lines.append(f"  {e.name}{suffix}")
    if len(entries) > max_entries:
        lines.append(f"  ... ({len(entries) - max_entries} more)")
    return "\n".join(lines)


def scan_and_build_prompt(project_root: Path) -> str:
    """Scan the project root and build a documentation generation prompt."""
    file_parts: list[str] = []

    for name in _SCAN_FILES:
        # Handle glob-style names with wildcards (docker-compose*.yml)
        if "*" in name:
            pattern = name.replace(".", r"\.").replace("*", ".*")
            import re
            matches = [
                f for f in project_root.iterdir()
                if re.match(pattern, f.name)
            ]
        else:
            matches = [project_root / name]

        for path in matches:
            if path.is_file():
                content = _read_file_capped(path)
                if content:
                    rel = os.path.relpath(path, project_root)
                    file_parts.append(f"### {rel}\n```\n{content}\n```")

    for dir_name in _SCAN_DIRS:
        dir_path = project_root / dir_name
        if dir_path.is_dir():
            listing = _scan_directory_listing(dir_path)
            if listing:
                file_parts.append(f"### {dir_name}/ (directory listing)\n{listing}")

    file_contents = "\n\n".join(file_parts) if file_parts else "(no scanned files found)"
    file_tree = _build_file_tree(project_root)

    required_docs_list = "\n".join(f"- `{d}`" for d in _REQUIRED_BASE_DOCS)
    conditional_docs_list = "\n".join(f"- `{d}`" for d in _CONDITIONAL_DOCS)

    return _INSTRUCTIONS_TEMPLATE.format(
        required_docs=required_docs_list,
        conditional_docs=conditional_docs_list,
        file_tree=file_tree,
        file_contents=file_contents,
    )
