"""Routes for project management and bootstrapping (T174, T181)."""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..models.schemas import (
    AgentLayoutFileDetail,
    AgentLayoutFileList,
    AgentLayoutJobStart,
    AgentLayoutJobStatus,
    AgentLayoutLogChunk,
    BootstrapResult,
    ProjectImportRequest,
    ProjectInfo,
)
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

    try:
        import runtime_db as _runtime_db
        artifact_reader = _runtime_db
    except ImportError:
        class _FallbackReader:
            def list_tickets(self, root):
                return []
        artifact_reader = _FallbackReader()

    projects = registry.list_projects(artifact_reader)

    runtime_base_root: Path | None = getattr(request.app.state, "runtime_base_root", None)
    if runtime_base_root is not None:
        enriched: list[ProjectInfo] = []
        for p in projects:
            # Prefer the persisted project_runtime_root from the registry so
            # the path stays stable even if env vars change after first import.
            persisted = registry.resolve_runtime_root(p.name)
            if persisted is not None:
                project_runtime_root_path = persisted
            else:
                project_runtime_root_path = runtime_base_root / p.name
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
    runtime_base_root: Path | None = getattr(request.app.state, "runtime_base_root", None)
    if runtime_base_root is None:
        raise HTTPException(
            status_code=503,
            detail="runtime_base_root is not configured — set RUNTIME_BASE_ROOT or AI_DEV_FACTORY_RUNTIME_ROOT",
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
            runtime_base_root=runtime_base_root,
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


def _supervisor_url() -> str:
    return os.environ.get(
        "AI_DEV_FACTORY_SUPERVISOR_URL", "http://host.docker.internal:8090"
    ).rstrip("/")


def _agent_layout_project_root(request: Request, project_id: str) -> Path:
    try:
        validate_project_id(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    registry = request.app.state.project_registry
    project_root = registry.resolve(project_id)
    if project_root is None:
        raise HTTPException(status_code=404, detail=f"project not found: {project_id}")
    return project_root


def _proxy_supervisor_get(path: str, params: dict | None = None) -> JSONResponse:
    """Forward a GET to the supervisor, propagating its status and body.

    Unlike the previous behaviour, non-2xx supervisor responses (404/422/5xx)
    are surfaced to the dashboard instead of being swallowed into an empty 200.
    """
    url = _supervisor_url()
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(f"{url}{path}", params=params or {})
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="supervisor unreachable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="supervisor timed out")
    try:
        body = resp.json()
    except ValueError:
        body = {"error": "invalid supervisor response", "detail": resp.text[:500]}
    return JSONResponse(status_code=resp.status_code, content=body)


@router.post("/{project_id}/install-agent-layout", response_model=AgentLayoutJobStart)
def install_agent_layout(project_id: str, request: Request):
    """Start an async agent-layout job; returns a job_id to poll for status/logs."""
    project_root = _agent_layout_project_root(request, project_id)
    url = _supervisor_url()
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{url}/projects/{project_id}/install-agent-layout",
                json={
                    "project_root": str(project_root),
                    "project_id": project_id,
                },
            )
        data = resp.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="supervisor unreachable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=503, detail="supervisor timed out starting agent layout")

    if resp.status_code >= 400:
        raise HTTPException(status_code=resp.status_code, detail=data.get("detail", data.get("error", "supervisor error")))

    return AgentLayoutJobStart(ok=bool(data.get("ok", True)), job_id=data["job_id"])


@router.get("/{project_id}/install-agent-layout/jobs")
def agent_layout_jobs(project_id: str, request: Request):
    _agent_layout_project_root(request, project_id)
    return _proxy_supervisor_get(f"/projects/{project_id}/install-agent-layout/jobs")


@router.get("/{project_id}/install-agent-layout/latest", response_model=AgentLayoutJobStatus)
def agent_layout_latest(project_id: str, request: Request):
    _agent_layout_project_root(request, project_id)
    return _proxy_supervisor_get(f"/projects/{project_id}/install-agent-layout/latest")


@router.get("/{project_id}/install-agent-layout/{job_id}", response_model=AgentLayoutJobStatus)
def agent_layout_job(project_id: str, job_id: str, request: Request):
    _agent_layout_project_root(request, project_id)
    return _proxy_supervisor_get(f"/projects/{project_id}/install-agent-layout/{job_id}")


@router.get("/{project_id}/install-agent-layout/{job_id}/logs", response_model=AgentLayoutLogChunk)
def agent_layout_logs(project_id: str, job_id: str, request: Request, offset: int = 0):
    _agent_layout_project_root(request, project_id)
    return _proxy_supervisor_get(
        f"/projects/{project_id}/install-agent-layout/{job_id}/logs", {"offset": offset}
    )


@router.get("/{project_id}/install-agent-layout/{job_id}/files", response_model=AgentLayoutFileList)
def agent_layout_files(project_id: str, job_id: str, request: Request):
    _agent_layout_project_root(request, project_id)
    return _proxy_supervisor_get(f"/projects/{project_id}/install-agent-layout/{job_id}/files")


@router.get("/{project_id}/install-agent-layout/{job_id}/file", response_model=AgentLayoutFileDetail)
def agent_layout_file(project_id: str, job_id: str, request: Request, path: str):
    _agent_layout_project_root(request, project_id)
    return _proxy_supervisor_get(
        f"/projects/{project_id}/install-agent-layout/{job_id}/file", {"path": path}
    )


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
