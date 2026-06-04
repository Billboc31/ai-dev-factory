"""Routes for project-context operations (T174)."""
from __future__ import annotations

import logging
import subprocess

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger("control-api")

router = APIRouter(prefix="/projects", tags=["projects"])


def _list_branches(project_root: str) -> list[str]:
    result = subprocess.run(
        ["git", "branch", "-a", "--sort=-committerdate", "--format=%(refname:short)"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=10,
    )
    seen: set[str] = set()
    branches: list[str] = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if not name:
            continue
        for prefix in ("origin/", "remotes/origin/"):
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        if name == "HEAD" or "->" in name:
            continue
        if name not in seen:
            seen.add(name)
            branches.append(name)
    return branches[:100]


@router.get("/{project_id}/branches")
def list_project_branches(project_id: str, request: Request) -> list[str]:
    registry = request.app.state.project_registry
    project_root = registry.resolve(project_id)
    if project_root is None:
        raise HTTPException(status_code=404, detail=f"project not found: {project_id}")
    try:
        return _list_branches(str(project_root))
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(status_code=500, detail="git branch listing timed out") from exc
    except Exception as exc:
        logger.exception("branches: failed to list branches for %s", project_id)
        raise HTTPException(status_code=500, detail=f"failed to list branches: {exc}") from exc
