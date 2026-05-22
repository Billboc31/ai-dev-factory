"""Builds the LLM prompt for AI-assisted operational scripts generation.

Pure string construction — no I/O, no LLM dependency.

The prompt is intentionally verbose about the "hard constraints" block.
Past runs (PR #114) produced outputs where the LLM:
  * wrapped shell code in triple-backtick markdown fences inside the
    FILE delimiters,
  * replaced ``healthcheck.sh`` / ``start.sh`` / ``stop.sh`` with a
    single-sentence English description,
  * truncated ``deployment.md`` to a one-line summary.

Those outputs were extracted by the parser and written to disk verbatim,
which broke the generated scripts. The hardened prompt + validator
(``scripts_validator``) together make such outputs fail BEFORE any
filesystem write or git commit happens.
"""
from __future__ import annotations

import json

# The block below is the strongest signal we can send to the LLM short of
# rewriting the entire prompt. It is placed FIRST so the model reads it
# before any of the contextual repo data.
_CRITICAL_CONSTRAINTS = """\
CRITICAL — READ BEFORE GENERATING ANYTHING.

The text you produce is parsed by a Python regex and each FILE block is
written **verbatim** to disk as the actual file content. The shell
scripts will be executed by `bash` on a developer machine that may have
unrelated daemons, projects and Docker stacks running side-by-side.
There is no human review step between your output and the filesystem.

You MUST obey every rule below. Any violation aborts the entire run.

## A. Output format

A1. `.sh` files MUST contain raw executable bash and nothing else.
A2. NEVER include ```` ```bash ````, ```` ``` ````, ```` ```sh ```` or
    any other markdown code fence inside a FILE block. The fences are
    for human-readable docs only. Inside a `.sh` FILE block, your first
    character must be `#`.
A3. Every `.sh` file MUST start with the exact line:
    `#!/usr/bin/env bash`
    followed by `set -euo pipefail`.
A4. NEVER replace a script body with a natural-language description
    (e.g. "Starts the supervisor → Docker stack → daemon"). The file is
    read by `bash`, not by a human.
A5. NEVER write meta-commentary inside FILE blocks ("Updated to cover
    …", "See deployment.md for details"). Each script must be a real
    implementation that runs.
A6. `deployment.md` MUST be a complete operational document with at
    least three Markdown headings (##) covering: overview, scripts,
    environment variables. Never replace it with a summary sentence.
A7. Output the seven FILE blocks below in order, with no text outside
    the delimiters.

## B. Safety — these scripts must NEVER affect unrelated processes

B1. Scripts MUST be project-scoped. The host machine may run other
    daemons, other compose stacks, other Python venvs. Your scripts
    must touch only this project's processes, ports, volumes and files.

B2. Preferred process-control order (most to least preferred):
      a. call the host supervisor HTTP API
         (e.g. `curl -sf $AI_DEV_FACTORY_SUPERVISOR_URL/daemon/stop`);
      b. read a project-local PID file and use `kill "$(cat …)"` or
         `pkill -F <pidfile>` (uppercase `-F` reads PIDs from a file —
         this is the safe form);
      c. project-specific process matching only as a last resort, and
         only with a pattern that uniquely identifies THIS project's
         processes (e.g. include the absolute project path or a
         project-scoped marker).

B3. NEVER use broad process killers:
      - `pkill -f run_daemon.py`   — would kill every developer's daemon
      - `pkill -f uvicorn`         — would kill every uvicorn on the box
      - `killall <name>`           — kills system-wide
    These are explicitly rejected by the validator.

B4. NEVER use `rm -rf` without an explicit guard. Acceptable patterns:
      - literal path under the project tree:
        `rm -rf "$PROJECT_ROOT/.ai-dev-factory/run"`
      - variable expansion with mandatory non-empty guard:
        `rm -rf "${TARGET:?TARGET must be set}"`
    Rejected patterns include `rm -rf /`, `rm -rf /*`, `rm -rf $HOME`,
    `rm -rf ~`, and `rm -rf "$VAR"` without `${VAR:?…}` guard.

B5. NEVER hard-code absolute user paths such as
    `/Users/<name>/...` or `/home/<name>/...`. Read them from
    `deploy/.env` via `$AI_DEV_FACTORY_RUNTIME_ROOT`,
    `$AI_DEV_FACTORY_PROJECT_ROOT`, `$HOST_RUNTIME_ROOT`,
    `$HOST_PROJECT_ROOT`, or compute them with `$(cd "$(dirname …)")`.

B6. NEVER use Docker commands with system-wide blast radius:
      - `docker system prune`              — wipes unrelated images
      - `docker container prune -f`        — wipes unrelated containers
      - `docker volume prune -f`           — wipes unrelated volumes
      - `docker compose down -v` (or `--volumes`) WITHOUT a
        `--project-name`/`-p` scoping flag — destroys volumes that may
        belong to other stacks.
    When you must call `docker compose`, source `deploy/.env` first and
    pass `--env-file deploy/.env` (and a project-name flag if you need
    explicit scoping).

B7. Scripts MUST be idempotent (safe to run twice) and dry-run friendly
    where possible. Detect already-running services before starting
    them again; detect already-stopped services before failing.

B8. Use the deploy/.env file as the single source of truth for paths,
    ports and supervisor URL. Source it explicitly:
    `[ -f deploy/.env ] && source deploy/.env || true`
"""

_INSTRUCTIONS_TEMPLATE = (
    _CRITICAL_CONSTRAINTS
    + """

You are an expert DevOps engineer. Using the repository information below, generate \
six operational shell scripts and updated deployment documentation.

Output exactly the seven sections below, each wrapped in the shown delimiters. \
Do not add any text outside the delimiters.

--- BEGIN FILE: .ai-dev-factory/scripts/bootstrap.sh ---
#!/usr/bin/env bash
set -euo pipefail
# Install all project dependencies and perform first-time setup.
# Replace this comment with real, idempotent setup steps (clone helpers,
# package installs, runtime directory creation, …).
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/scripts/build.sh ---
#!/usr/bin/env bash
set -euo pipefail
# Build the project (compile, bundle, container images, …).
# Replace this comment with real, idempotent build steps.
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/scripts/start.sh ---
#!/usr/bin/env bash
set -euo pipefail
# Start all project services. Detect and handle already-running processes.
# Replace this comment with the actual startup commands.
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/scripts/stop.sh ---
#!/usr/bin/env bash
set -euo pipefail
# Gracefully stop all project services.
#
# Prefer this order, per safety rule B2:
#   1. POST to the supervisor /daemon/stop endpoint (read URL from env).
#   2. Read PID files from .ai-dev-factory/run/*.pid and `kill "$(cat …)"`.
#   3. Only fall back to project-specific process matching with a unique
#      project-scoped marker — never `pkill -f run_daemon.py` (B3).
#
# Replace this comment with real shutdown logic.
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/scripts/restart.sh ---
#!/usr/bin/env bash
set -euo pipefail
# Thin wrapper around stop.sh then start.sh.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/stop.sh"
bash "$SCRIPT_DIR/start.sh"
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/scripts/healthcheck.sh ---
#!/usr/bin/env bash
set -euo pipefail
# Exit 0 when the system is healthy, non-zero otherwise.
# Replace this comment with real probes per service from the deploy profile.
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/deployment.md ---
# Deployment Guide

## Overview
…

## Scripts
…

## Environment variables
…

(Replace each `…` with real content — keep these three sections at minimum.)
--- END FILE ---

Repository scan result (JSON):
<SCAN_JSON>

Deploy profile (YAML) — use this as the authoritative source for services and healthcheck:
<DEPLOY_PROFILE_YAML>

Repository file tree (max depth 4):
<FILE_TREE>
"""
)


def build_scripts_prompt(
    project_root: str,
    scan_result: dict,
    deploy_profile_yaml: str,
    file_tree: str,
) -> str:
    """Assemble the scripts generation prompt from project context."""
    return (
        _INSTRUCTIONS_TEMPLATE
        .replace("<SCAN_JSON>", json.dumps(scan_result, indent=2))
        .replace("<DEPLOY_PROFILE_YAML>", deploy_profile_yaml or "(not available)")
        .replace("<FILE_TREE>", file_tree)
    )
