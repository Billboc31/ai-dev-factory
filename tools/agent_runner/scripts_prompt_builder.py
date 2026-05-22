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
scripts will be executed by `bash`. There is no human review step
between your output and the filesystem.

You MUST obey every rule below. Any violation aborts the entire run.

1. `.sh` files MUST contain raw executable bash and nothing else.
2. NEVER include ```` ```bash ````, ```` ``` ````, ```` ```sh ```` or
   any other markdown code fence inside a FILE block. The fences are
   for human-readable docs only. Inside a `.sh` FILE block, your first
   character must be `#`.
3. Every `.sh` file MUST start with the exact line:
   `#!/usr/bin/env bash`
   followed by `set -euo pipefail`.
4. NEVER replace a script body with a natural-language description
   (e.g. "Starts the supervisor → Docker stack → daemon"). The file is
   read by `bash`, not by a human.
5. NEVER write meta-commentary inside FILE blocks ("Updated to cover
   …", "See deployment.md for details"). Each script must be a real
   implementation that runs.
6. Scripts must be idempotent (safe to run twice) and use absolute
   paths via `$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)` or
   equivalent.
7. `deployment.md` MUST be a complete operational document with at
   least three Markdown headings (##) covering: overview, scripts,
   environment variables. Never replace it with a summary sentence.
8. Output the seven FILE blocks below in order, with no text outside
   the delimiters.
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
# Replace this comment with the actual shutdown commands.
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
