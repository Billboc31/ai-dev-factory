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
from worktree_manager import (  # noqa: E402
    create_ticket_branch_and_worktree,
    get_ticket_worktree_path,
    remove_ticket_worktree,
)

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
    parser.add_argument("--worktrees-dir", default=None)
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    project_id = args.project_id
    exec_cmd = args.exec_cmd
    worktrees_dir = Path(args.worktrees_dir).resolve() if args.worktrees_dir else None

    # When the supervisor injected SANDBOX_WORKTREE, use that isolated directory
    # for all file writes and git operations instead of the main project root.
    sandbox_worktree = os.environ.get("SANDBOX_WORKTREE", "").strip()
    effective_root = Path(sandbox_worktree).resolve() if sandbox_worktree else project_root

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
    job_id = f"analysis-{project_id}-{ts}"
    worktree_path: Path | None = None

    started_at = _now()
    _write_state(project_id, {
        "state": "running",
        "started_at": started_at,
        "finished_at": None,
        "error": None,
        "branch": None,
        "pr_url": None,
        "worktree_path": None,
    })
    logger.info("analysis started project_id=%s root=%s", project_id, project_root)

    try:
        if worktrees_dir is not None:
            ok, msg = create_ticket_branch_and_worktree(
                job_id, f"analysis/{job_id}", worktrees_dir, repo_root=project_root
            )
            if not ok:
                raise RuntimeError(f"failed to create analysis worktree: {msg}")
            worktree_path = get_ticket_worktree_path(job_id, worktrees_dir)
            logger.info("analysis worktree created: %s", worktree_path)
            _write_state(project_id, {
                "state": "running",
                "started_at": started_at,
                "finished_at": None,
                "error": None,
                "branch": None,
                "pr_url": None,
                "worktree_path": str(worktree_path),
            })

        # T135: isolated analysis worktree (highest priority) wins for I/O.
        # T136: otherwise, write into the sandbox worktree when SANDBOX_WORKTREE
        # is set; falling back to the canonical project_root preserves the
        # original single-tree behavior.
        write_root = worktree_path if worktree_path is not None else effective_root

        logger.info("scanning project")
        scan_result = _scan_project(effective_root)

        logger.info("building file tree")
        file_tree = _build_file_tree(effective_root)

        logger.info("building analysis prompt")
        prompt = build_analysis_prompt(str(effective_root), scan_result, file_tree)

        logger.info("invoking LLM via exec_cmd=%r", exec_cmd.split()[0])
        llm_output = _invoke_llm(exec_cmd, prompt, effective_root)

        logger.info("parsing LLM output (%d chars)", len(llm_output))
        generated_files = _extract_files(llm_output)

        required = (".ai-dev-factory/deploy.yml", ".ai-dev-factory/deployment.md")
        for rel in required:
            if rel not in generated_files:
                raise RuntimeError(f"LLM output missing required block: {rel}")

        logger.info("writing %d generated file(s)", len(generated_files))
        # T135: when --worktrees-dir is passed we created an isolated analysis
        # worktree (`worktree_path`) and write into it.
        # T136: otherwise, if the supervisor injected SANDBOX_WORKTREE,
        # `effective_root` already points at the sandbox copy — write there.
        # Otherwise fall back to the canonical project root.
        (write_root / ".ai-dev-factory").mkdir(exist_ok=True)
        for rel_path, content in generated_files.items():
            target = (write_root / rel_path).resolve()
            if not str(target).startswith(str(write_root) + "/"):
                raise RuntimeError(
                    f"LLM returned path escaping project root: {rel_path}"
                )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logger.info("wrote %s", rel_path)

        deploy_path = write_root / ".ai-dev-factory" / "deploy.yml"
        try:
            import yaml as _yaml
            _yaml.safe_load(deploy_path.read_text(encoding="utf-8"))
            logger.info("deploy.yml YAML validation passed")
        except ImportError:
            logger.warning("pyyaml not available — skipping deploy.yml validation")
        except Exception as exc:
            raise RuntimeError(f"deploy.yml is not valid YAML: {exc}") from exc

        logger.info("committing and pushing")
        # Commit/push from the same root we wrote into so the diff is captured.
        branch, pr_url = commit_and_push(write_root, project_id)

        finished_at = _now()
        _write_state(project_id, {
            "state": "success",
            "started_at": started_at,
            "finished_at": finished_at,
            "error": None,
            "branch": branch,
            "pr_url": pr_url,
            "worktree_path": str(worktree_path) if worktree_path is not None else None,
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
            "worktree_path": str(worktree_path) if worktree_path is not None else None,
        })
        sys.exit(1)

    finally:
        if worktrees_dir is not None and worktree_path is not None:
            ok, msg = remove_ticket_worktree(job_id, worktrees_dir, force=True)
            if not ok:
                logger.warning("failed to remove analysis worktree %s: %s", job_id, msg)
            else:
                logger.info("analysis worktree removed: %s", job_id)


if __name__ == "__main__":
    main()
