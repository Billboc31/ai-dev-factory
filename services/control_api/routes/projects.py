"""Routes for project management and bootstrapping (T174, T181)."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..models.schemas import BootstrapResult, ProjectImportRequest, ProjectInfo
from ..services.project_bootstrap import bootstrap
from ..services.project_id import validate_project_id

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


@router.get("", response_model=list[ProjectInfo])
def list_projects(request: Request) -> list[ProjectInfo]:
    """Return all registered projects with runtime_root and stack fields."""
    registry = request.app.state.project_registry
    runtime_root: Path | None = getattr(request.app.state, "runtime_root", None)

    try:
        import runtime_db as _runtime_db
        artifact_reader = _runtime_db
    except ImportError:
        class _FallbackReader:
            def list_tickets(self, root):
                return []
        artifact_reader = _FallbackReader()

    projects = registry.list_projects(artifact_reader)

    if runtime_root is not None:
        enriched: list[ProjectInfo] = []
        for p in projects:
            project_runtime_root_path = runtime_root / "projects" / p.name
            stack = _read_stack(Path(p.root))
            enriched.append(ProjectInfo(
                name=p.name,
                root=p.root,
                tickets_count=p.tickets_count,
                runtime_root=str(project_runtime_root_path) if project_runtime_root_path.is_dir() else None,
                stack=stack,
            ))
        return enriched

    return projects


def _read_stack(project_root: Path) -> str | None:
    yml = project_root / ".ai-dev-factory" / "project.yml"
    if not yml.exists():
        return None
    for line in yml.read_text(encoding="utf-8").splitlines():
        if line.startswith("stack:"):
            return line.split(":", 1)[1].strip()
    return None


@router.post("/import", response_model=BootstrapResult)
def import_project(body: ProjectImportRequest, request: Request):
    """Bootstrap an existing git repository as an ai-dev-factory project."""
    runtime_root: Path | None = getattr(request.app.state, "runtime_root", None)
    if runtime_root is None:
        raise HTTPException(
            status_code=503,
            detail="runtime_root is not configured — set AI_DEV_FACTORY_RUNTIME_ROOT",
        )

    try:
        validate_project_id(body.project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    project_root = Path(body.project_root).expanduser().resolve()
    if not project_root.exists():
        raise HTTPException(status_code=422, detail=f"path does not exist: {project_root}")

    registry = request.app.state.project_registry

    try:
        result = bootstrap(
            project_root=project_root,
            project_id=body.project_id,
            runtime_root=runtime_root,
            registry=registry,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("projects: bootstrap failed for %s", body.project_id)
        raise HTTPException(status_code=500, detail=f"bootstrap failed: {exc}") from exc

    return BootstrapResult(**result.__dict__)


@router.delete("/{project_id}")
def delete_project(project_id: str, request: Request):
    """Unregister a project from the workspace registry."""
    try:
        validate_project_id(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    registry = request.app.state.project_registry
    try:
        registry.unregister(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return {"ok": True}


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
