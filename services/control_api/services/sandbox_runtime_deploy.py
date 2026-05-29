"""Shared operational deploy pipeline for sandboxes and named environments.

Executes the same steps as ``tools/agent_runner/run_sandbox.py``:

  ensure infra → per-sandbox supervisor → Traefik routes → operational
  scripts (bootstrap, build, start, healthcheck) → optional smoke (validation)

Deployer branch deploy uses :mod:`deployer_runner` (``deploy.yml``). Sandbox
and Environment runtimes use this module — the host-side script pipeline.
"""
from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..models.sandbox import SandboxState, SandboxStatus
from .infra_service_manager import resolve_proxy_routes_dir
from .proxy_manager import ProxyManager, build_sandbox_urls

logger = logging.getLogger("control-api")

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class OperationalDeployResult:
    success: bool
    error: str | None = None
    urls: dict[str, str] = field(default_factory=dict)
    supervisor_pid: int | None = None
    steps: list[dict] = field(default_factory=list)
    healthcheck_status: str = "skipped"
    smoke_status: str = "skipped"
    route_registered: bool = False


def _import_run_sandbox():
    """Lazy import of host worker helpers (same code path as Deploy & Test)."""
    from tools.agent_runner import run_sandbox as rs  # noqa: WPS433

    return rs


def _extra_env_for_state(state: SandboxState, sandbox_dir: Path) -> dict[str, str]:
    urls = state.urls or build_sandbox_urls(
        state.id, web_host=state.web_host, api_host=state.api_host
    )
    runtime_root = sandbox_dir / "runtime"
    return {
        "API_PORT": str(state.ports.get("api", 8080)),
        "WEB_PORT": str(state.ports.get("web", 3000)),
        "COMPOSE_PROJECT_NAME": state.compose_project,
        "SANDBOX_ID": state.id,
        "SANDBOX_WEB_URL": urls["web"],
        "SANDBOX_API_URL": urls["api"],
        "AI_DEV_FACTORY_SUPERVISOR_PORT": str(state.supervisor_port),
        "AI_DEV_FACTORY_SUPERVISOR_URL": (
            f"http://host.docker.internal:{state.supervisor_port}"
        ),
        "AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL": (
            f"http://127.0.0.1:{state.supervisor_port}"
        ),
        "AI_DEV_FACTORY_RUNTIME_ROOT": str(runtime_root),
        "AI_DEV_FACTORY_PROJECT_ROOT": state.project_root,
    }


def deploy_operational_runtime(
    state: SandboxState,
    *,
    sandbox_dir: Path,
    mode: str = "environment",
    use_worktree: bool = False,
) -> OperationalDeployResult:
    """Run bootstrap → start scripts, supervisor, and Traefik for *state*.

    *sandbox_dir* must already contain ``.env`` / ``state.json`` from
    :meth:`SandboxManager.create`.
    """
    rs = _import_run_sandbox()
    sandbox_dir = sandbox_dir.resolve()
    log_path = sandbox_dir / "run.log"
    runtime_root = sandbox_dir / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    for subdir in ("state", "logs", "runs"):
        (runtime_root / subdir).mkdir(exist_ok=True)

    state_path = sandbox_dir / "state.json"
    latest_state_path = sandbox_dir / "pipeline-state.json"
    project_root = Path(state.project_root).resolve()
    worktree_path = sandbox_dir / "worktree" if use_worktree else project_root

    urls = build_sandbox_urls(
        state.id, web_host=state.web_host, api_host=state.api_host
    )
    extra_env = _extra_env_for_state(state, sandbox_dir)

    state_base = {
        "state": "validating",
        "mode": mode,
        "sandbox_id": state.id,
        "project_id": state.env_name or state.ticket_id,
        "started_at": _now_iso(),
        "finished_at": None,
        "error": None,
        "last_step": "supervisor",
        "steps": [],
        "ports": {"api_port": state.ports["api"], "web_port": state.ports["web"]},
        "worktree_path": str(worktree_path),
        "compose_project": state.compose_project,
        "project_root": str(project_root),
    }
    rs._append_log(log_path, f"\n=== operational deploy {state.id} mode={mode} ===\n")

    supervisor_proc = rs._start_sandbox_supervisor(
        state.supervisor_port, runtime_root, log_path
    )
    if supervisor_proc is None:
        return OperationalDeployResult(
            success=False,
            error="sandbox supervisor failed to start on host runtime",
        )
    extra_env["AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED"] = "1"
    supervisor_pid = supervisor_proc.pid

    rs._ensure_required_infra(log_path)
    routes_dir = resolve_proxy_routes_dir()
    try:
        registered_urls = ProxyManager(
            routes_dir=routes_dir,
            auto_ensure_infra=False,
        ).register(
            state.id,
            state.ports,
            web_host=state.web_host,
            api_host=state.api_host,
        )
    except Exception as exc:
        rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
        return OperationalDeployResult(
            success=False,
            error=f"proxy route registration failed: {exc}",
            supervisor_pid=supervisor_pid,
        )

    route_file = routes_dir / f"{state.id}.yml"
    if not route_file.exists():
        rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
        return OperationalDeployResult(
            success=False,
            error="proxy route file was not created on host runtime",
            supervisor_pid=supervisor_pid,
        )

    rs._append_log(
        log_path,
        f"proxy: route registered sandbox={state.id} dir={routes_dir} urls={registered_urls}\n",
    )
    probe_url = registered_urls.get("api") or urls["api"]
    if not rs._wait_for_proxy_url(probe_url, log_path):
        rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
        ProxyManager(routes_dir=routes_dir, auto_ensure_infra=False).unregister(
            state.id
        )
        return OperationalDeployResult(
            success=False,
            error="reverse proxy route did not become reachable on host runtime",
            urls=registered_urls,
            supervisor_pid=supervisor_pid,
            route_registered=True,
        )

    if use_worktree:
        ok, wt_error = rs._create_worktree(project_root, worktree_path, log_path)
        if not ok:
            rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
            ProxyManager(routes_dir=routes_dir, auto_ensure_infra=False).unregister(
                state.id
            )
            return OperationalDeployResult(
                success=False,
                error=wt_error or "worktree creation failed",
                urls=registered_urls,
                supervisor_pid=supervisor_pid,
                route_registered=True,
            )

    success, script_error, steps = rs._run_scripts(
        worktree_path,
        state_path,
        latest_state_path,
        log_path,
        state_base,
        extra_env=extra_env,
    )

    healthcheck_status = "skipped"
    for step in steps:
        if step.get("name") == "healthcheck.sh":
            healthcheck_status = step.get("status", "skipped")

    smoke_status = "skipped"
    if success and mode == "validation":
        smoke_status, smoke_fail = rs._run_smoke_tests(
            worktree_path, log_path, extra_env
        )
        if smoke_fail is not None:
            success = False
            script_error = "smoke tests failed"

    rs._write_validation_json(
        runtime_root,
        state.id,
        healthcheck_status,
        smoke_status,
        steps[-1]["name"] if steps else None,
        registered_urls,
        {"api_port": state.ports["api"], "web_port": state.ports["web"]},
        state_base["started_at"],
        log_path,
    )

    if not success:
        rs._run_stop_script(worktree_path, log_path, extra_env)
        rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
        ProxyManager(routes_dir=routes_dir, auto_ensure_infra=False).unregister(
            state.id
        )
        return OperationalDeployResult(
            success=False,
            error=script_error or "operational scripts failed",
            urls=registered_urls,
            supervisor_pid=supervisor_pid,
            steps=steps,
            healthcheck_status=healthcheck_status,
            smoke_status=smoke_status,
            route_registered=True,
        )

    rs._append_log(log_path, f"\n=== operational deploy {state.id} ready ===\n")
    return OperationalDeployResult(
        success=True,
        urls=registered_urls,
        supervisor_pid=supervisor_pid,
        steps=steps,
        healthcheck_status=healthcheck_status,
        smoke_status=smoke_status,
        route_registered=True,
    )


def apply_deploy_result_to_state(
    state: SandboxState, result: OperationalDeployResult
) -> SandboxState:
    """Merge a successful deploy result into sandbox state for the dashboard."""
    if not result.success:
        return state.model_copy(update={"status": SandboxStatus.error})
    return state.model_copy(
        update={
            "status": SandboxStatus.running,
            "urls": result.urls,
            "supervisor_pid": result.supervisor_pid,
            "deployed_at": _now_iso(),
        }
    )
