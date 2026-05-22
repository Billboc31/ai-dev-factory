#!/usr/bin/env python3
"""Host-side scripts generation worker for AI-assisted operational scripts.

Invoked by the supervisor as a background subprocess. Receives project context,
calls the configured LLM runtime, writes generated scripts (chmod 0o755) and
deployment.md, then creates a PR. All output goes to the scripts log file.
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
import stat
import subprocess
import sys
from pathlib import Path

_RUNNER_DIR = Path(__file__).resolve().parent
if str(_RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(_RUNNER_DIR))

from scripts_prompt_builder import build_scripts_prompt  # noqa: E402
from scripts_git_service import commit_and_push  # noqa: E402
from scripts_validator import validate_generated_files  # noqa: E402

logger = logging.getLogger("run_scripts")

_SKIP_DIRS = frozenset({
    ".git", "__pycache__", "node_modules", ".venv", "venv",
    ".mypy_cache", ".ruff_cache", ".pytest_cache", ".tox", "dist", "build",
})

_FILE_BLOCK_RE = re.compile(
    r"--- BEGIN FILE: (.+?) ---\n(.*?)--- END FILE ---",
    re.DOTALL,
)

_REQUIRED_SCRIPTS = (
    ".ai-dev-factory/scripts/bootstrap.sh",
    ".ai-dev-factory/scripts/build.sh",
    ".ai-dev-factory/scripts/start.sh",
    ".ai-dev-factory/scripts/stop.sh",
    ".ai-dev-factory/scripts/restart.sh",
    ".ai-dev-factory/scripts/healthcheck.sh",
    ".ai-dev-factory/deployment.md",
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
    return base / f"scripts-{project_id}.json"


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


def _load_deploy_profile_yaml(project_root: Path) -> str:
    deploy_path = project_root / ".ai-dev-factory" / "deploy.yml"
    if deploy_path.exists():
        return deploy_path.read_text(encoding="utf-8")
    return ""


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
    parser = argparse.ArgumentParser(description="AI-assisted operational scripts generation worker")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--exec-cmd", required=True)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    project_id = args.project_id
    exec_cmd = args.exec_cmd

    # When the supervisor injected SANDBOX_WORKTREE, use that isolated directory
    # for all file writes and git operations instead of the main project root.
    sandbox_worktree = os.environ.get("SANDBOX_WORKTREE", "").strip()
    effective_root = Path(sandbox_worktree).resolve() if sandbox_worktree else project_root

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
    logger.info("scripts generation started project_id=%s root=%s", project_id, project_root)

    try:
        logger.info("scanning project")
        scan_result = _scan_project(effective_root)

        logger.info("loading deploy profile")
        deploy_profile_yaml = _load_deploy_profile_yaml(effective_root)

        logger.info("building file tree")
        file_tree = _build_file_tree(effective_root)

        logger.info("building scripts prompt")
        prompt = build_scripts_prompt(str(effective_root), scan_result, deploy_profile_yaml, file_tree)

        logger.info("invoking LLM via exec_cmd=%r", exec_cmd.split()[0])
        llm_output = _invoke_llm(exec_cmd, prompt, effective_root)

        logger.info("parsing LLM output (%d chars)", len(llm_output))
        generated_files = _extract_files(llm_output)

        if not generated_files:
            raise RuntimeError(
                "LLM output contained no parseable FILE blocks "
                "(no `--- BEGIN FILE: ... ---` / `--- END FILE ---` pairs)"
            )

        logger.info("validating generated scripts (%d file blocks)", len(generated_files))
        validation_errors = validate_generated_files(
            generated_files, required=_REQUIRED_SCRIPTS
        )
        if validation_errors:
            for err in validation_errors:
                logger.error("validation failed: %s", err)
            logger.error(
                "generation aborted before commit: %d validation error(s) — "
                "no files written, no git operation performed",
                len(validation_errors),
            )
            raise RuntimeError(
                "scripts validation failed:\n  - "
                + "\n  - ".join(validation_errors)
            )
        logger.info("validation passed — all %d file(s) look like real artifacts",
                    len(generated_files))

        logger.info("writing %d generated file(s)", len(generated_files))
        (effective_root / ".ai-dev-factory" / "scripts").mkdir(parents=True, exist_ok=True)
        for rel_path, content in generated_files.items():
            target = (effective_root / rel_path).resolve()
            if not str(target).startswith(str(effective_root) + "/"):
                raise RuntimeError(
                    f"LLM returned path escaping project root: {rel_path}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            if rel_path.endswith(".sh"):
                target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            logger.info("wrote %s", rel_path)

        logger.info("committing and pushing")
        branch, pr_url = commit_and_push(effective_root, project_id)

        finished_at = _now()
        _write_state(project_id, {
            "state": "success",
            "started_at": started_at,
            "finished_at": finished_at,
            "error": None,
            "branch": branch,
            "pr_url": pr_url,
        })
        logger.info("scripts generation complete branch=%s pr_url=%s", branch, pr_url)

    except Exception as exc:  # noqa: BLE001
        finished_at = _now()
        logger.error("scripts generation failed: %s", exc)
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
