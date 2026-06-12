"""Routes for project management and bootstrapping (T174, T181)."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..models.schemas import BootstrapResult, ProjectImportRequest, ProjectInfo
from ..services.project_bootstrap import bootstrap
from ..services.project_id import validate_project_id

logger = logging.getLogger("control-api")

router = APIRouter(prefix="/projects", tags=["projects"])


def _supervisor_validate_path(project_root: str) -> dict:
    """Call supervisor POST /projects/validate-path. Returns the response dict.

    Raises HTTPException on network failure so callers get a clean 503.
    """
    url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "http://host.docker.internal:8090").rstrip("/")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(f"{url}/projects/validate-path", json={"project_root": project_root})
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="supervisor unreachable — cannot validate host path")
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="supervisor timed out during path validation")


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
            project_root_path = Path(p.root)
            stack = _read_stack(project_root_path)
            github_repo = _read_github_repo(project_root_path)
            enriched.append(ProjectInfo(
                name=p.name,
                root=p.root,
                tickets_count=p.tickets_count,
                runtime_root=str(project_runtime_root_path) if project_runtime_root_path.is_dir() else None,
                stack=stack,
                github_repo=github_repo,
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


def _read_github_repo(project_root: Path) -> str | None:
    import re
    deploy_yml = project_root / ".ai-dev-factory" / "deploy.yml"
    if not deploy_yml.exists():
        return None
    m = re.search(r'--issue-repo\s+(\S+)', deploy_yml.read_text(encoding="utf-8"))
    return m.group(1) if m else None


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

    validated = _supervisor_validate_path(body.project_root)
    if "error" in validated:
        _error_map = {
            "path_not_found": f"path does not exist: {validated.get('detail', body.project_root)}",
            "not_a_directory": f"path is not a directory: {validated.get('detail', body.project_root)}",
            "permission_denied": f"permission denied: {validated.get('detail', body.project_root)}",
        }
        detail = _error_map.get(validated["error"], validated.get("detail", validated["error"]))
        raise HTTPException(status_code=422, detail=detail)

    if not validated.get("is_git_repo"):
        raise HTTPException(
            status_code=422,
            detail=f"not a git repository: {validated.get('resolved_path', body.project_root)}",
        )

    registry = request.app.state.project_registry

    try:
        result = bootstrap(
            project_root=validated["resolved_path"],
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
