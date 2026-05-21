#!/usr/bin/env python3
"""Host-side analysis worker for AI-assisted operational project analysis.

Invoked by the supervisor as a background subprocess. Receives project context,
calls the configured LLM runtime, writes generated files, and creates a PR.
All output goes to the analysis log file via the supervisor's stdout/stderr redirect.
"""
from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
if str(_RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(_RUNNER_DIR))

from analysis_prompt_builder import build_analysis_prompt  # noqa: E402
from analysis_git_service import commit_and_push  # noqa: E402

logger = logging.getLogger("run_analysis")

_SKIP_DIRS = frozenset({
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", ".tox", "dist", "build",
})

_FILE_BLOCK_RE = re.compile(
    r"--- BEGIN FILE: (.+?) ---\n(.*?)--- END FILE ---",
    re.DOTALL,
)


def _now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _state_path(project_id: str) -> Path:
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        base = Path(runtime_root) / "state"
    else:
        factory_root = os.environ.get("AI_DEV_FACTORY_PROJECT_ROOT")
        base = (Path(factory_root) if factory_root else _RUNNER_DIR.parents[1]) / "state"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"analysis-{project_id}.json"


def _write_state(project_id: str, data: dict) -> None:
    _state_path(project_id).write_text(json.dumps(data, indent=2), encoding="utf-8")


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


def _scan_project(project_root: Path) -> dict:
    """Minimal project scan — avoids importing the services package."""
    docker_services: list[str] = []
    for name in ("docker-compose.yml", "docker-compose.yaml"):
        compose = project_root / name
        if compose.exists():
            try:
                import yaml
                data = yaml.safe_load(compose.read_text(encoding="utf-8"))
                services = data.get("services") if isinstance(data, dict) else None
                if isinstance(services, dict):
                    docker_services = list(services.keys())
            except Exception:
                pass
            break

    return {
        "docker_services": docker_services,
        "python_backend": (
            (project_root / "requirements.txt").exists()
            or (project_root / "pyproject.toml").exists()
        ),
        "node_frontend": (project_root / "package.json").exists(),
        "required_tools": [
            t for t in ("gh", "git", "docker", "claude") if shutil.which(t)
        ],
    }


def _invoke_llm(exec_cmd: str, prompt: str, project_root: Path) -> str:
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
        raise RuntimeError(f"LLM execution failed (exit {result.returncode}): {snippet}")
    return result.stdout


def _extract_files(llm_output: str) -> dict[str, str]:
    return {
        match.group(1).strip(): match.group(2)
        for match in _FILE_BLOCK_RE.finditer(llm_output)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="AI-assisted project analysis worker")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--exec-cmd", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    project_id = args.project_id
    exec_cmd = args.exec_cmd

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    started_at = _now()
    _write_state(project_id, {
        "state": "running",
        "started_at": started_at,
        "finished_at": None,
        "error": None,
        "branch": None,
        "pr_url": None,
    })
    logger.info("analysis started project_id=%s root=%s", project_id, project_root)

    try:
        logger.info("scanning project")
        scan_result = _scan_project(project_root)

        logger.info("building file tree")
        file_tree = _build_file_tree(project_root)

        logger.info("building analysis prompt")
        prompt = build_analysis_prompt(str(project_root), scan_result, file_tree)

        logger.info("invoking LLM via exec_cmd=%r", exec_cmd.split()[0])
        llm_output = _invoke_llm(exec_cmd, prompt, project_root)

        logger.info("parsing LLM output (%d chars)", len(llm_output))
        generated_files = _extract_files(llm_output)

        required = (".ai-dev-factory/deploy.yml", ".ai-dev-factory/deployment.md")
        for rel in required:
            if rel not in generated_files:
                raise RuntimeError(f"LLM output missing required block: {rel}")

        logger.info("writing %d generated file(s)", len(generated_files))
        ai_dir = project_root / ".ai-dev-factory"
        ai_dir.mkdir(exist_ok=True)
        for rel_path, content in generated_files.items():
            target = project_root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logger.info("wrote %s", rel_path)

        logger.info("committing and pushing")
        branch, pr_url = commit_and_push(project_root, project_id)

        finished_at = _now()
        _write_state(project_id, {
            "state": "success",
            "started_at": started_at,
            "finished_at": finished_at,
            "error": None,
            "branch": branch,
            "pr_url": pr_url,
        })
        logger.info("analysis complete branch=%s pr_url=%s", branch, pr_url)

    except Exception as exc:  # noqa: BLE001
        finished_at = _now()
        logger.error("analysis failed: %s", exc)
        _write_state(project_id, {
            "state": "failed",
            "started_at": started_at,
            "finished_at": finished_at,
            "error": str(exc),
            "branch": None,
            "pr_url": None,
        })
        sys.exit(1)


if __name__ == "__main__":
    main()
