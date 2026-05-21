"""Builds the LLM prompt for AI-assisted project operational documentation generation.

Pure string construction — no I/O, no LLM dependency.
"""
from __future__ import annotations

import json

_DEPLOY_PROFILE_SCHEMA = """\
{
  "version": 1,
  "project": "<project name>",
  "required_tools": ["<tool1>", "<tool2>"],
  "components": [
    {
      "name": "<component name>",
      "type": "docker",
      "service": "<docker-compose service name>"
    },
    {
      "name": "<component name>",
      "type": "host",
      "command": "<shell command to start the process>"
    }
  ],
  "healthcheck": {
    "command": "<shell command — exits 0 when healthy>",
    "timeout": 30,
    "retries": 3,
    "delay": 5
  }
}"""

_INSTRUCTIONS_TEMPLATE = """\
You are an expert DevOps engineer. Analyze the repository described below and generate \
operational documentation and a deployment profile.

Output exactly the three sections below, each wrapped in the shown delimiters. \
Do not add any text outside the delimiters.

--- BEGIN FILE: .ai-dev-factory/deploy.yml ---
<YAML content that matches the DeployProfile schema — infer all components and healthcheck>
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/deployment.md ---
<Markdown documentation covering: project overview, prerequisites, build commands, \
startup commands, restart procedure, healthcheck procedure, environment variables, \
runtime dependencies, known operational constraints>
--- END FILE ---

--- BEGIN FILE: .ai-dev-factory/runtime-notes.md ---
<Markdown notes on edge cases, platform-specific concerns, or observed technical debt \
relevant to operations. Write "N/A" if nothing notable.>
--- END FILE ---

DeployProfile schema (the deploy.yml must be valid YAML that matches this structure):
<DEPLOY_SCHEMA>

Infer the following fields (leave as empty list / null if unknown):
- required_tools: CLI tools that must be present on the host (e.g. git, docker, gh)
- components: every runnable service or process
  - docker services → type=docker, service=<compose service name>
  - host processes  → type=host, command=<startup shell command>
- healthcheck: a single shell command that exits 0 when the system is healthy

Repository scan result (JSON):
<SCAN_JSON>

Repository file tree (max depth 4):
<FILE_TREE>
"""


def build_analysis_prompt(project_root: str, scan_result: dict, file_tree: str) -> str:
    """Assemble the analysis prompt from scan data and file tree."""
    return (
        _INSTRUCTIONS_TEMPLATE
        .replace("<DEPLOY_SCHEMA>", _DEPLOY_PROFILE_SCHEMA)
        .replace("<SCAN_JSON>", json.dumps(scan_result, indent=2))
        .replace("<FILE_TREE>", file_tree)
    )
