"""Bootstrap an existing git repository as an ai-dev-factory project."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

logger = logging.getLogger("control-api")


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
    clones_dir: str = ""


def _supervisor_url() -> str:
    url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "http://host.docker.internal:8090")
    return url.rstrip("/")


def _call_supervisor(
    method: str,
    path: str,
    json_body: dict | None = None,
    timeout: float = 30.0,
) -> tuple[dict | None, str | None]:
    """Call the supervisor API. Returns (data, error_code)."""
    url = _supervisor_url()
    full_url = f"{url}{path}"
    try:
        with httpx.Client(timeout=timeout) as client:
            if method == "GET":
                resp = client.get(full_url)
            else:
                resp = client.post(full_url, json=json_body or {})
        return resp.json(), None
    except httpx.ConnectError:
        return None, "supervisor_unreachable"
    except httpx.TimeoutException:
        return None, "supervisor_unreachable"


def bootstrap(
    project_root: str | Path,
    project_id: str,
    runtime_base_root: Path,
    registry,
) -> BootstrapResult:
    """Bootstrap project_root as an isolated ai-dev-factory project via supervisor.

    Delegates all host filesystem operations to the supervisor so the Control
    API can run in Docker without direct access to host paths.
    """
    from .project_id import assert_contained, validate_project_id

    validate_project_id(project_id)
    assert_contained(runtime_base_root, project_id)

    data, err = _call_supervisor("POST", "/projects/bootstrap", {
        "project_root": str(project_root),
        "project_id": project_id,
        "runtime_root": str(runtime_base_root),
    })

    if err:
        raise RuntimeError(f"supervisor unreachable: {err}")

    if "error" in data:
        error_code = data["error"]
        detail = data.get("detail", error_code)
        if error_code == "path_not_found":
            raise ValueError(f"path does not exist: {detail}")
        if error_code == "not_a_directory":
            raise ValueError(f"path is not a directory: {detail}")
        if error_code == "git_not_found":
            raise ValueError(f"project_root is not a git repository: {detail}")
        if error_code == "permission_denied":
            raise ValueError(f"permission denied: {detail}")
        raise RuntimeError(f"bootstrap failed: {detail}")

    logger.info(
        "bootstrap: project_id=%s project_root=%s runtime=%s",
        data["project_id"], data["project_root"], data["runtime_root"],
    )

    registry.register(project_id, Path(data["project_root"]))

    return BootstrapResult(
        project_id=data["project_id"],
        project_root=data["project_root"],
        runtime_root=data["runtime_root"],
        stack=data["stack"],
        runs_dir=data["runs_dir"],
        logs_dir=data["logs_dir"],
        state_dir=data["state_dir"],
        worktrees_dir=data["worktrees_dir"],
        clones_dir=data.get("clones_dir", ""),
    )


def auto_bootstrap(
    project_root: Path,
    project_id: str,
    runtime_base_root: Path | None,
    registry,
) -> None:
    """Idempotent startup registration for the current AI Dev Factory repo.

    Unlike bootstrap(), this function:
    - Never raises (logs warnings instead).
    - Accepts runtime_base_root=None to skip bootstrap and just register.
    - Uses ensure_registered (idempotent) instead of register.
    """
    from .project_id import validate_project_id

    try:
        validate_project_id(project_id)
    except ValueError:
        logger.warning("auto_bootstrap: invalid project_id %r — skipping", project_id)
        return

    if runtime_base_root is not None:
        data, err = _call_supervisor("POST", "/projects/bootstrap", {
            "project_root": str(project_root),
            "project_id": project_id,
            "runtime_root": str(runtime_base_root),
        })

        if err:
            logger.warning(
                "auto_bootstrap: supervisor unreachable (%s) — registering without bootstrap",
                err,
            )
        elif "error" in data:
            logger.warning(
                "auto_bootstrap: supervisor returned error %s — registering without bootstrap",
                data["error"],
            )
        else:
            logger.info(
                "auto_bootstrap: project_id=%s project_root=%s runtime_root=%s",
                project_id, data["project_root"], data["runtime_root"],
            )
            registry.ensure_registered(project_id, Path(data["project_root"]))
            return

    registry.ensure_registered(project_id, Path(str(project_root)))
