"""Bootstrap an existing git repository as an ai-dev-factory project."""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("control-api")

_PROJECT_YML_FILENAME = "project.yml"
_AI_DEV_FACTORY_DIR = ".ai-dev-factory"


@dataclass
class BootstrapResult:
    project_id: str
    project_root: str
    runtime_root: str
    stack: str
    runs_dir: str
    logs_dir: str
    state_dir: str
    worktrees_dir: str


def bootstrap(
    project_root: Path,
    project_id: str,
    runtime_root: Path,
    registry,
) -> BootstrapResult:
    """Bootstrap *project_root* as an isolated ai-dev-factory project.

    Steps:
    1. Validate project_id and assert path containment.
    2. Verify project_root is a git repository.
    3. Create per-project runtime directory tree.
    4. Write .ai-dev-factory/project.yml into the repo (if absent).
    5. Register the project in the workspace registry.
    6. Return BootstrapResult with all resolved paths.
    """
    from .project_id import assert_contained, validate_project_id
    from .stack_detector import detect_stack

    validate_project_id(project_id)
    project_runtime_root = assert_contained(runtime_root, project_id)

    project_root = project_root.resolve()
    if not (project_root / ".git").is_dir():
        raise ValueError(f"project_root is not a git repository: {project_root}")

    runs_dir = project_runtime_root / "runs"
    logs_dir = project_runtime_root / "logs"
    state_dir = project_runtime_root / "state"
    worktrees_dir = project_runtime_root / "worktrees"

    for d in (runs_dir, logs_dir, state_dir, worktrees_dir):
        d.mkdir(parents=True, exist_ok=True)

    logger.info(
        "bootstrap: project_id=%s project_root=%s project_runtime_root=%s",
        project_id, project_root, project_runtime_root,
    )

    stack = detect_stack(project_root)

    ai_dev_dir = project_root / _AI_DEV_FACTORY_DIR
    project_yml = ai_dev_dir / _PROJECT_YML_FILENAME
    if not project_yml.exists():
        ai_dev_dir.mkdir(exist_ok=True)
        bootstrapped_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        project_yml.write_text(
            f"name: {project_id}\nstack: {stack}\nbootstrapped_at: {bootstrapped_at}\n",
            encoding="utf-8",
        )
        logger.info("bootstrap: wrote %s", project_yml)

    registry.register(project_id, project_root)

    return BootstrapResult(
        project_id=project_id,
        project_root=str(project_root),
        runtime_root=str(project_runtime_root),
        stack=stack,
        runs_dir=str(runs_dir),
        logs_dir=str(logs_dir),
        state_dir=str(state_dir),
        worktrees_dir=str(worktrees_dir),
    )
