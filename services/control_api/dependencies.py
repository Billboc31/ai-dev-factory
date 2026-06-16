from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request


def resolve_project(project_id: str, request: Request) -> Path:
    """FastAPI dependency: resolve project_id → project_root via the registry.

    Raises HTTP 404 when the project_id is not registered.
    """
    registry = request.app.state.project_registry
    root = registry.resolve(project_id)
    if root is None:
        raise HTTPException(status_code=404, detail=f"project {project_id!r} not found")
    return root


def resolve_project_runtime_root(project_id: str, request: Request) -> Path | None:
    """FastAPI dependency: return the persisted project_runtime_root, or None."""
    registry = request.app.state.project_registry
    return registry.resolve_runtime_root(project_id)
