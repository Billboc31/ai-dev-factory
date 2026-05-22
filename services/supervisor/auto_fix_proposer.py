"""Generic AI auto-fix proposer for sandbox deployment failures.

Architecture (called inline by the supervisor, not as a subprocess worker)::

    Supervisor endpoint (POST /auto-fix/{project_id}/propose)
      → background thread
        → collect_failure_context  (reads deploy.yml, sandbox state/logs, scripts)
        → call_ai_runtime          (subprocess via exec_cmd — mirrors _invoke_llm)
        → validate_patches         (path-safety check)
        → persist_proposal         (writes state.json under runtime_root)

No provider SDK, no hardcoded service names, ports, or framework assumptions.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shlex
import subprocess
import uuid
from pathlib import Path

_ALLOWED_PREFIX = ".ai-dev-factory/scripts"


# ── Context collection ────────────────────────────────────────────────────────

def collect_failure_context(
    sandbox_id: str,
    project_root: Path,
    runtime_root: Path | None = None,
) -> dict:
    """Collect generic failure context — no hardcoded service/port/framework assumptions."""
    rt = _resolve_runtime_root(runtime_root, project_root)

    context: dict = {
        "sandbox_id": sandbox_id,
        "deploy_profile": "",
        "sandbox_state": {},
        "logs": [],
        "operational_scripts": {},
    }

    deploy_path = project_root / ".ai-dev-factory" / "deploy.yml"
    if deploy_path.exists():
        try:
            context["deploy_profile"] = deploy_path.read_text(encoding="utf-8")
        except OSError:
            pass

    state_path = rt / "sandboxes" / sandbox_id / "state.json"
    if state_path.exists():
        try:
            context["sandbox_state"] = json.loads(state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    log_path = rt / "sandboxes" / sandbox_id / "run.log"
    if log_path.exists():
        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")
            context["logs"] = text.splitlines()[-200:]
        except OSError:
            pass

    scripts_dir = project_root / ".ai-dev-factory" / "scripts"
    if scripts_dir.exists():
        for script_file in sorted(scripts_dir.iterdir()):
            if script_file.is_file():
                try:
                    context["operational_scripts"][script_file.name] = (
                        script_file.read_text(encoding="utf-8")
                    )
                except OSError:
                    pass

    return context


def _resolve_runtime_root(explicit: Path | None, project_root: Path) -> Path:
    if explicit is not None:
        return explicit
    env = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if env:
        return Path(env)
    return project_root / ".ai-dev-factory"


# ── AI runtime invocation ─────────────────────────────────────────────────────

def _build_prompt(context: dict, failing_step: str | None) -> str:
    parts = [
        "You are an AI assistant analyzing a sandbox deployment failure.",
        "Analyze the failure context and propose targeted fixes to operational scripts.",
        "",
        "## Failing Step",
        failing_step or "unknown",
        "",
        "## Deploy Profile",
        context.get("deploy_profile") or "(not found)",
        "",
        "## Sandbox State",
        json.dumps(context.get("sandbox_state") or {}, indent=2),
        "",
        "## Recent Logs (last 200 lines)",
        "\n".join(context.get("logs") or []),
        "",
        "## Operational Scripts",
    ]
    for name, content in (context.get("operational_scripts") or {}).items():
        parts.append(f"### {name}")
        parts.append(content)
        parts.append("")
    parts += [
        "## Instructions",
        "Respond ONLY with a valid JSON array. Each element must be an object with:",
        '  {"relative_path": ".ai-dev-factory/scripts/<filename>", '
        '"content": "<full corrected file content>", '
        '"reasoning": "<why this change fixes the failure>"}',
        "Only propose changes to files inside .ai-dev-factory/scripts/.",
        "If no changes are needed, respond with an empty array: []",
        "",
        "Your response must start with [ and end with ].",
    ]
    return "\n".join(parts)


def call_ai_runtime(
    context: dict,
    exec_cmd: str,
    project_root: Path,
    failing_step: str | None = None,
) -> list[dict]:
    """Invoke the AI runtime via exec_cmd subprocess.

    Mirrors ``_invoke_llm`` from ``tools/agent_runner/run_scripts.py``.
    Raises RuntimeError on non-zero exit, ValueError on malformed output.
    """
    prompt = _build_prompt(context, failing_step)
    cmd_parts = shlex.split(exec_cmd) + ["--print"]
    result = subprocess.run(
        cmd_parts,
        input=prompt,
        capture_output=True,
        text=True,
        cwd=str(project_root),
        timeout=300,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    if result.returncode != 0:
        snippet = (result.stderr or "")[:500]
        raise RuntimeError(f"AI runtime failed (exit {result.returncode}): {snippet}")

    output = result.stdout.strip()
    match = re.search(r"\[.*\]", output, re.DOTALL)
    if not match:
        raise ValueError(f"AI output did not contain a JSON array: {output[:300]!r}")

    patches = json.loads(match.group(0))
    if not isinstance(patches, list):
        raise ValueError(f"AI output JSON was not an array: {type(patches)}")
    return patches


# ── Patch validation ──────────────────────────────────────────────────────────

def _is_allowed_path(relative_path: str) -> bool:
    """Return True iff path is safely inside .ai-dev-factory/scripts/."""
    if not relative_path:
        return False
    if ".." in relative_path:
        return False
    normalized = relative_path.lstrip("/").replace("\\", "/")
    return normalized.startswith(_ALLOWED_PREFIX + "/")


def validate_patches(patches: list[dict], project_root: Path) -> list[dict]:  # noqa: ARG001
    """Annotate patches with valid=True/False based on allowed path check."""
    return [
        {
            "relative_path": p.get("relative_path", ""),
            "content": p.get("content", ""),
            "valid": _is_allowed_path(p.get("relative_path", "")),
        }
        for p in patches
    ]


# ── Persistence ───────────────────────────────────────────────────────────────

def make_proposal_id() -> str:
    return uuid.uuid4().hex[:12]


def _now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def make_proposal(
    proposal_id: str,
    project_id: str,
    sandbox_id: str | None,
    failing_step: str | None,
) -> dict:
    return {
        "proposal_id": proposal_id,
        "project_id": project_id,
        "sandbox_id": sandbox_id,
        "failing_step": failing_step,
        "status": "pending",
        "reasoning": None,
        "patches": [],
        "context_snapshot": {},
        "created_at": _now_utc(),
        "error": None,
    }


def persist_proposal(project_id: str, proposal: dict, runtime_root: Path) -> None:
    """Write proposal to {runtime_root}/auto-fix-proposals/{project_id}/{proposal_id}/state.json."""
    path = runtime_root / "auto-fix-proposals" / project_id / proposal["proposal_id"] / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")


def load_proposal(project_id: str, proposal_id: str, runtime_root: Path) -> dict | None:
    """Load a proposal by ID. Returns None if not found or unreadable."""
    path = runtime_root / "auto-fix-proposals" / project_id / proposal_id / "state.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_proposals(project_id: str, runtime_root: Path) -> list[dict]:
    """List all proposals for a project sorted by created_at ascending."""
    base = runtime_root / "auto-fix-proposals" / project_id
    if not base.exists():
        return []
    results = []
    for state_file in base.glob("*/state.json"):
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            results.append(data)
        except (json.JSONDecodeError, OSError):
            pass
    return sorted(results, key=lambda x: x.get("created_at", ""))
