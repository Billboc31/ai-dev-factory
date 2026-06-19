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
    agent_layout_branch: str | None = None
    agent_layout_pr_url: str | None = None
    agent_layout_pr_number: int | None = None
    agent_layout_error: str | None = None


def _supervisor_url() -> str:
    url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "http://host.docker.internal:8090")
    return url.rstrip("/")


def _ensure_project_runtime_db(project_id: str) -> None:
    """Best-effort ensure the shared runtime store exists (Postgres backend only).

    The Postgres backend uses ONE database with project-scoped rows, so there is
    no per-project database to create — this only guarantees the shared schema
    is present (idempotent). It is intentionally best-effort and NON-BLOCKING:
    a failure here is logged and ignored so it can never leave a half-registered
    project. The same schema is also ensured lazily on first runtime access
    (API startup, daemon startup), so registration never depends on it.

    With the SQLite backend this is a no-op (single shared file, created on demand).
    """
    if os.environ.get("RUNTIME_DB_BACKEND", "sqlite").strip().lower() != "postgres":
        return
    try:
        import importlib.util

        tools = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
        spec = importlib.util.spec_from_file_location("_rdb_bootstrap", tools / "runtime_db.py")
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        handle = mod.get_db_path(project_id)
        mod.init_runtime_db(handle)
        logger.info("runtime_db: ensured shared store for project %s (%s)", project_id, handle)
    except Exception:
        logger.warning(
            "runtime_db: could not pre-init shared store for %s — will init lazily on first access",
            project_id, exc_info=True,
        )


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
        if error_code == "runtime_base_root_not_writable":
            raise ValueError(f"runtime base root is not writable: {detail}")
        raise RuntimeError(f"bootstrap failed: {detail}")

    logger.info(
        "bootstrap: project_id=%s project_root=%s runtime=%s",
        data["project_id"], data["project_root"], data["runtime_root"],
    )

    registry.register(
        project_id,
        Path(data["project_root"]),
        project_runtime_root=Path(data["runtime_root"]),
    )
    _ensure_project_runtime_db(project_id)

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
        agent_layout_branch=data.get("agent_layout_branch"),
        agent_layout_pr_url=data.get("agent_layout_pr_url"),
        agent_layout_pr_number=data.get("agent_layout_pr_number"),
        agent_layout_error=data.get("agent_layout_error"),
    )


def auto_bootstrap(
    project_root: Path,
    project_id: str,
    runtime_base_root: Path | None,
    registry,
    self_runtime_root: Path | None = None,
) -> None:
    """Idempotent startup registration for the current AI Dev Factory repo.

    Unlike bootstrap(), this function:
    - Never raises (logs warnings instead).
    - Accepts runtime_base_root=None to skip bootstrap and just register.
    - Uses ensure_registered (idempotent) instead of register.
    - When no multi-project base is configured, registers the project with
      *self_runtime_root* (AI_DEV_FACTORY_RUNTIME_ROOT) as its own runtime root.
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
            registry.ensure_registered(
                project_id,
                Path(data["project_root"]),
                project_runtime_root=Path(data["runtime_root"]),
            )
            _ensure_project_runtime_db(project_id)
            return

    registry.ensure_registered(
        project_id,
        Path(str(project_root)),
        project_runtime_root=self_runtime_root,
    )
    _ensure_project_runtime_db(project_id)
