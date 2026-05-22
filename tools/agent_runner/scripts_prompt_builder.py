"""Builds the LLM prompt for AI-assisted operational scripts generation.

Pure string construction — no I/O, no LLM dependency.
"""
from __future__ import annotations

import json

_INSTRUCTIONS_TEMPLATE = """\
You are an expert DevOps engineer. Using the repository information below, generate \
six operational shell scripts and updated deployment documentation.

Output exactly the seven sections below, each wrapped in the shown delimiters. \
Do not add any text outside the delimiters. All scripts must be executable bash \
(shebang #!/usr/bin/env bash, set -euo pipefail).

--- BEGIN FILE: .ai-dev-factory/scripts/bootstrap.sh ---
<Script to install all project dependencies and perform first-time setup. \
Should be idempotent.>
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/scripts/build.sh ---
<Script to build the project (compile, bundle, container images, etc.). \
Should be idempotent.>
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/scripts/start.sh ---
<Script to start all project services. Should check for already-running \
processes and handle them gracefully.>
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/scripts/stop.sh ---
<Script to gracefully stop all project services.>
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/scripts/restart.sh ---
<Script that calls stop.sh then start.sh. Should be a thin wrapper.>
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/scripts/healthcheck.sh ---
<Script that exits 0 when the system is healthy and non-zero otherwise. \
Should check each service defined in the deploy profile.>
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/deployment.md ---
<Markdown documentation covering: project overview, prerequisites, \
how to use each script (bootstrap, build, start, stop, restart, healthcheck), \
environment variables, runtime dependencies, known operational constraints.>
--- END FILE ---

Repository scan result (JSON):
<SCAN_JSON>

Deploy profile (YAML) — use this as the authoritative source for services and healthcheck:
<DEPLOY_PROFILE_YAML>

Repository file tree (max depth 4):
<FILE_TREE>
"""


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
