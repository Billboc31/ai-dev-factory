"""Host-side environment provisioning (Supervisor runtime).

All filesystem access and :class:`SandboxManager` operations for named
environments run here so containerized Control API processes never call
``Path.exists()`` on host-only paths.
"""
from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from ..models.sandbox import (
    EnvironmentMode,
    EnvironmentType,
    LifecyclePhase,
    RefType,
    SandboxState,
    SandboxStatus,
)
from .sandbox_manager import SandboxManager, SandboxNotFoundError
from .sandbox_runtime_deploy import (
    OperationalDeployResult,
    apply_deploy_failure,
    apply_deploy_result_to_state,
    deploy_operational_runtime,
)

logger = logging.getLogger("control-api")

_DNS_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$|^[a-z0-9]$")
_RESERVED_PREFIXES = ("traefik.", "_")
_RESERVED_EXACT = {"localhost"}
_HOST_RULE_RE = re.compile(r"Host\(`([^`]+)`\)")


def validate_host_format(host: str) -> str | None:
    """Return an error message if *host* is invalid, else None."""
    if not host:
        return "host cannot be empty"
    if host in _RESERVED_EXACT:
        return f"reserved host: {host!r}"
    for prefix in _RESERVED_PREFIXES:
        if host.startswith(prefix):
            return f"reserved host prefix in {host!r}"
    for label in host.split("."):
        if not _DNS_LABEL_RE.match(label):
            return (
                f"invalid DNS label {label!r} in {host!r} — "
                "use lowercase alphanumeric and hyphens only"
            )
    return None


def declared_traefik_hosts(routes_dir: Path) -> set[str]:
    hosts: set[str] = set()
    if not routes_dir.exists():
        return hosts
    for yml in routes_dir.glob("*.yml"):
        if yml.stem.startswith("_"):
            continue
        try:
            for m in _HOST_RULE_RE.finditer(yml.read_text(encoding="utf-8")):
                hosts.add(m.group(1))
        except OSError:
            pass
    return hosts


def map_environment_paths(
    project_root: str,
    sandbox_path: str | None,
    map_fn: Callable[[str], str],
) -> tuple[str, str | None]:
    """Map container-side paths to host paths via the supervisor mapper."""
    host_project = str(Path(map_fn(project_root)).expanduser().resolve())
    host_sandbox: str | None = None
    if sandbox_path:
        host_sandbox = str(Path(map_fn(sandbox_path)).expanduser().resolve())
    return host_project, host_sandbox


def validate_project_root_on_host(host_project_root: str) -> None:
    if not Path(host_project_root).is_dir():
        raise ValueError(
            f"project_root does not exist on host runtime: {host_project_root}"
        )


def _validate_runtime_consistency(
    host_project: str,
    host_sandbox: str | None,
) -> None:
    """Fail early when runtime paths would be ambiguous or overlapping."""
    if host_sandbox is None:
        return
    project = Path(host_project).resolve()
    sandbox = Path(host_sandbox).resolve()
    if project == sandbox:
        raise ValueError(
            f"runtime mismatch: project_root and sandbox_path resolve to the same path: {project} — "
            "sandbox would overwrite the live project checkout"
        )
    if sandbox.is_relative_to(project):
        raise ValueError(
            f"runtime mismatch: sandbox_path {sandbox} is inside project_root {project} — "
            "sandbox runtime files would be created inside the source repository"
        )
    if project.is_relative_to(sandbox):
        raise ValueError(
            f"runtime mismatch: project_root {project} is inside sandbox_path {sandbox} — "
            "deploy scripts would be sourced from within the sandbox root"
        )
    if not sandbox.parent.exists():
        raise ValueError(
            f"runtime mismatch: sandbox_path parent directory does not exist: {sandbox.parent}"
        )


def _get_repo_url(project_root: str) -> str:
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=5,
        )
        url = result.stdout.strip()
        return url if url else project_root
    except Exception:
        return project_root


def _validate_traefik_hosts(
    web_host: str | None,
    api_host: str | None,
    routes_dir: Path,
) -> None:
    for field, host in (("web_host", web_host), ("api_host", api_host)):
        if host is None:
            continue
        err = validate_host_format(host)
        if err:
            raise ValueError(f"{field}: {err}")
    if not (web_host or api_host):
        return
    declared = declared_traefik_hosts(routes_dir)
    for field, host in (("web_host", web_host), ("api_host", api_host)):
        if host and host in declared:
            raise ValueError(f"{field}: host already in use: {host!r}")


def provision_environment(
    mgr: SandboxManager,
    *,
    env_name: str,
    project_root: str,
    map_fn: Callable[[str], str],
    project_id: str | None = None,
    ref: str | None = None,
    ref_type: RefType | None = None,
    env_type: EnvironmentType | None = None,
    deployment_mode: EnvironmentMode | None = None,
    web_host: str | None = None,
    api_host: str | None = None,
    sandbox_path: str | None = None,
    runtime_root: str | None = None,
    force_source_refresh: bool = False,
) -> SandboxState:
    """Create and start an environment on the host filesystem."""
    host_project, host_sandbox = map_environment_paths(
        project_root, sandbox_path, map_fn
    )
    validate_project_root_on_host(host_project)
    _validate_runtime_consistency(host_project, host_sandbox)
    _validate_traefik_hosts(web_host, api_host, mgr._proxy.routes_dir)

    repo_url = _get_repo_url(host_project)
    logger.info(
        "project_id=%s repo_url=%s branch=%s environment=%s project_root=%s sandbox_path=%s",
        project_id or "(unset)",
        repo_url,
        ref or "(default)",
        env_name,
        host_project,
        host_sandbox or "(default)",
    )

    state = mgr.create(
        ticket_id=env_name,
        project_root=host_project,
        env_name=env_name,
        env_type=env_type,
        ref=ref,
        ref_type=ref_type,
        deployment_mode=deployment_mode,
        web_host=web_host,
        api_host=api_host,
        sandbox_path=host_sandbox,
    )
    state = state.model_copy(
        update={
            "status": SandboxStatus.creating,
            "lifecycle_phase": LifecyclePhase.provisioning,
            "runtime_root": runtime_root,
            "force_source_refresh": force_source_refresh,
        }
    )
    mgr._write_state(state)
    sandbox_dir = mgr._storage_dir(state.id)

    def _persist(updated: SandboxState) -> None:
        nonlocal state
        state = updated
        mgr._write_state(state)

    try:
        result = deploy_operational_runtime(
            state,
            sandbox_dir=sandbox_dir,
            mode="environment",
            persist_state=_persist,
        )
    except Exception as exc:
        failed = apply_deploy_failure(
            state,
            OperationalDeployResult(success=False, error=str(exc)),
        )
        mgr._write_state(failed)
        raise RuntimeError(f"environment provisioning failed: {exc}") from exc
    if not result.success:
        failed = apply_deploy_failure(state, result)
        mgr._write_state(failed)
        raise RuntimeError(
            f"environment provisioning failed: {result.error or 'operational deploy failed'}"
        )
    started = apply_deploy_result_to_state(state, result)
    mgr._write_state(started)
    return started


def redeploy_environment(mgr: SandboxManager, env_id: str) -> SandboxState:
    """Re-run the full operational deploy lifecycle for an existing environment."""
    try:
        state = mgr._read_state(env_id)
    except SandboxNotFoundError as exc:
        raise exc
    if state.env_name is None:
        raise ValueError(f"not an environment sandbox: {env_id}")

    mgr.stop(env_id)
    state = mgr._read_state(env_id)
    state = state.model_copy(
        update={
            "status": SandboxStatus.creating,
            "lifecycle_phase": LifecyclePhase.provisioning,
            "lifecycle_error": None,
            "urls": {},
            "supervisor_pid": None,
        }
    )
    mgr._write_state(state)
    sandbox_dir = mgr._storage_dir(env_id)

    def _persist(updated: SandboxState) -> None:
        nonlocal state
        state = updated
        mgr._write_state(state)

    try:
        result = deploy_operational_runtime(
            state,
            sandbox_dir=sandbox_dir,
            mode="environment",
            persist_state=_persist,
        )
    except Exception as exc:
        failed = apply_deploy_failure(
            state,
            OperationalDeployResult(success=False, error=str(exc)),
        )
        mgr._write_state(failed)
        raise RuntimeError(f"environment redeploy failed: {exc}") from exc

    if not result.success:
        failed = apply_deploy_failure(state, result)
        mgr._write_state(failed)
        raise RuntimeError(
            f"environment redeploy failed: {result.error or 'operational deploy failed'}"
        )

    started = apply_deploy_result_to_state(state, result)
    mgr._write_state(started)
    return started


def provision_environment_from_body(
    mgr: SandboxManager,
    body: dict[str, Any],
    map_fn: Callable[[str], str],
) -> SandboxState:
    return provision_environment(
        mgr,
        env_name=body["env_name"],
        project_root=body["project_root"],
        project_id=body.get("project_id"),
        map_fn=map_fn,
        ref=body.get("ref"),
        ref_type=body.get("ref_type"),
        env_type=body.get("env_type"),
        deployment_mode=body.get("deployment_mode"),
        web_host=body.get("web_host"),
        api_host=body.get("api_host"),
        sandbox_path=body.get("sandbox_path"),
        runtime_root=body.get("runtime_root"),
        force_source_refresh=body.get("force_source_refresh", False),
    )


def _destroy_quietly(mgr: SandboxManager, sandbox_id: str) -> None:
    try:
        mgr.destroy(sandbox_id)
    except Exception as exc:
        logger.warning(
            "environment cleanup failed: sandbox_id=%s error=%s",
            sandbox_id,
            exc,
        )
