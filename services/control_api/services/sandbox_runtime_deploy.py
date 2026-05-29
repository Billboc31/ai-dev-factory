"""Shared operational deploy pipeline for sandboxes and named environments.

Executes the same steps as ``tools/agent_runner/run_sandbox.py``:

  ensure infra → per-sandbox supervisor → Traefik routes → operational
  scripts (bootstrap, build, start, healthcheck) → smoke (when configured)

Deployer branch deploy uses :mod:`deployer_runner` (``deploy.yml``). Sandbox
and Environment runtimes use this module — the host-side script pipeline.
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..models.sandbox import EnvironmentMode, LifecyclePhase, SandboxState, SandboxStatus
from .infra_service_manager import resolve_proxy_routes_dir
from .proxy_manager import ProxyManager, build_sandbox_urls
from .proxy_route_files import route_file_path, validate_route_file

logger = logging.getLogger("control-api")

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_SCRIPT_PHASE: dict[str, LifecyclePhase] = {
    "bootstrap.sh": LifecyclePhase.bootstrapping,
    "build.sh": LifecyclePhase.building,
    "start.sh": LifecyclePhase.starting,
    "healthcheck.sh": LifecyclePhase.healthchecking,
}


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
    last_step: str | None = None


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


def _should_run_smoke(state: SandboxState, mode: str) -> bool:
    if mode == "validation":
        return True
    return (
        mode == "environment"
        and state.deployment_mode == EnvironmentMode.deploy_and_test
    )


def format_environment_logs(
    sandbox_dir: Path,
    state: SandboxState,
    *,
    docker_component: str | None = None,
) -> str:
    """Aggregate lifecycle logs for the environments dashboard."""
    sandbox_dir = sandbox_dir.resolve()
    sections: list[str] = []

    run_log = sandbox_dir / "run.log"
    if run_log.exists():
        sections.append(
            "=== Lifecycle (bootstrap / build / start / healthcheck / smoke) ===\n"
            + run_log.read_text(encoding="utf-8", errors="replace")
        )

    supervisor_log = sandbox_dir / "runtime" / "supervisor.log"
    if supervisor_log.exists():
        sections.append(
            "=== Supervisor ===\n"
            + supervisor_log.read_text(encoding="utf-8", errors="replace")
        )

    pipeline_path = sandbox_dir / "pipeline-state.json"
    if pipeline_path.exists():
        sections.append(
            "=== Pipeline state ===\n"
            + pipeline_path.read_text(encoding="utf-8", errors="replace")
        )

    validation_path = sandbox_dir / "runtime" / "validation.json"
    if validation_path.exists():
        sections.append(
            "=== Validation ===\n"
            + validation_path.read_text(encoding="utf-8", errors="replace")
        )

    if state.lifecycle_steps:
        sections.append(
            "=== Step summary ===\n"
            + json.dumps(state.lifecycle_steps, indent=2)
        )

    if state.lifecycle_error:
        sections.append(f"=== Last error ===\n{state.lifecycle_error}\n")

    docker_section = _docker_logs_section(state, docker_component)
    if docker_section:
        sections.append(docker_section)

    if not sections:
        return "(no lifecycle logs yet — provisioning may still be in progress)"
    return "\n\n".join(sections)


def _docker_logs_section(
    state: SandboxState, component: str | None
) -> str:
    env_file = Path(state.env_file) if state.env_file else None
    if env_file is None or not env_file.exists():
        sandbox_dir_guess = Path(state.sandbox_dir) if state.sandbox_dir else None
        if sandbox_dir_guess:
            env_file = sandbox_dir_guess / ".env"
    if env_file is None or not env_file.exists():
        return ""

    cmd = [
        "docker",
        "compose",
        "-p",
        state.compose_project,
        "--env-file",
        str(env_file),
        "logs",
        "--no-color",
        "--tail",
        "200",
    ]
    if component:
        cmd.append(component)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=state.project_root,
        check=False,
    )
    body = (result.stdout or result.stderr or "").strip()
    if not body:
        return ""
    return f"=== Docker compose logs (debug) ===\n{body}\n"


def deploy_operational_runtime(
    state: SandboxState,
    *,
    sandbox_dir: Path,
    mode: str = "environment",
    use_worktree: bool = False,
    persist_state: Callable[[SandboxState], None] | None = None,
) -> OperationalDeployResult:
    """Run bootstrap → start scripts, supervisor, and Traefik for *state*.

    Pipeline progress is written to ``pipeline-state.json`` (not ``state.json``).
    Optional *persist_state* updates :class:`SandboxState` for live UI polling.
    """
    rs = _import_run_sandbox()
    sandbox_dir = sandbox_dir.resolve()
    log_path = sandbox_dir / "run.log"
    runtime_root = sandbox_dir / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    for subdir in ("state", "logs", "runs"):
        (runtime_root / subdir).mkdir(exist_ok=True)

    pipeline_state_path = sandbox_dir / "pipeline-state.json"
    project_root = Path(state.project_root).resolve()
    worktree_path = sandbox_dir / "worktree" if use_worktree else project_root

    urls = build_sandbox_urls(
        state.id, web_host=state.web_host, api_host=state.api_host
    )
    extra_env = _extra_env_for_state(state, sandbox_dir)
    current: list[SandboxState] = [state]

    def _persist(
        phase: LifecyclePhase,
        *,
        last_step: str | None = None,
        lifecycle_error: str | None = None,
        **extra: object,
    ) -> None:
        if persist_state is None:
            return
        updates: dict = {
            "lifecycle_phase": phase,
            "last_step": last_step,
            "lifecycle_error": lifecycle_error,
            **extra,
        }
        if phase == LifecyclePhase.failed:
            updates["status"] = SandboxStatus.error
        current[0] = current[0].model_copy(update=updates)
        persist_state(current[0])

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
    _persist(LifecyclePhase.provisioning, last_step="supervisor")

    supervisor_proc = rs._start_sandbox_supervisor(
        state.supervisor_port, runtime_root, log_path
    )
    if supervisor_proc is None:
        _persist(
            LifecyclePhase.failed,
            last_step="supervisor",
            lifecycle_error="sandbox supervisor failed to start on host runtime",
        )
        return OperationalDeployResult(
            success=False,
            error="sandbox supervisor failed to start on host runtime",
            last_step="supervisor",
        )
    extra_env["AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED"] = "1"
    supervisor_pid = supervisor_proc.pid

    rs._ensure_required_infra(log_path)
    routes_dir = resolve_proxy_routes_dir()
    registered_urls: dict[str, str] = {}
    route_registered = False

    def _register_proxy_routes_after_compose() -> str | None:
        """Attach Traefik to the compose network and write route file."""
        nonlocal registered_urls, route_registered
        _persist(LifecyclePhase.provisioning, last_step="routes")
        try:
            registered_urls = ProxyManager(
                routes_dir=routes_dir,
                auto_ensure_infra=False,
            ).register(
                state.id,
                web_host=state.web_host,
                api_host=state.api_host,
                log=lambda line: rs._append_log(log_path, line),
            )
        except Exception as exc:
            return f"proxy route registration failed: {exc}"
        route_file = route_file_path(routes_dir, state.id)
        err = validate_route_file(route_file)
        if err:
            return err
        route_registered = True
        rs._append_log(
            log_path,
            f"proxy: route registered sandbox={state.id} dir={routes_dir} urls={registered_urls}\n",
        )
        probe_url = registered_urls.get("api") or urls["api"]
        if not rs._wait_for_proxy_url(probe_url, log_path):
            return "reverse proxy route did not become reachable on host runtime"
        return None

    if use_worktree:
        ok, wt_error = rs._create_worktree(project_root, worktree_path, log_path)
        if not ok:
            rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
            err = wt_error or "worktree creation failed"
            _persist(LifecyclePhase.failed, last_step="worktree", lifecycle_error=err)
            return OperationalDeployResult(
                success=False,
                error=err,
                urls=registered_urls,
                supervisor_pid=supervisor_pid,
                route_registered=True,
                last_step="worktree",
            )

    def _on_step_start(script_name: str) -> None:
        phase = _SCRIPT_PHASE.get(script_name, LifecyclePhase.provisioning)
        _persist(phase, last_step=script_name)

    def _on_step_complete(script_name: str) -> bool | None:
        if script_name != "start.sh":
            return None
        route_err = _register_proxy_routes_after_compose()
        return route_err is None

    success, script_error, steps = rs._run_scripts(
        worktree_path,
        pipeline_state_path,
        pipeline_state_path,
        log_path,
        state_base,
        extra_env=extra_env,
        on_step_start=_on_step_start if persist_state else None,
        on_step_complete=_on_step_complete,
    )

    healthcheck_status = "skipped"
    for step in steps:
        if step.get("name") == "healthcheck.sh":
            healthcheck_status = step.get("status", "skipped")

    smoke_status = "skipped"
    if success and _should_run_smoke(state, mode):
        _persist(LifecyclePhase.validating, last_step="smoke.sh")
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

    if persist_state:
        current[0] = current[0].model_copy(
            update={
                "lifecycle_steps": steps,
                "healthcheck_status": healthcheck_status,
                "smoke_status": smoke_status,
            }
        )
        persist_state(current[0])

    if not success:
        rs._run_stop_script(worktree_path, log_path, extra_env)
        rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
        ProxyManager(routes_dir=routes_dir, auto_ensure_infra=False).unregister(
            state.id,
            compose_project=state.compose_project,
            remove_route_file=False,
        )
        err = script_error or "operational scripts failed"
        _persist(
            LifecyclePhase.failed,
            last_step=steps[-1]["name"] if steps else "scripts",
            lifecycle_error=err,
            lifecycle_steps=steps,
            healthcheck_status=healthcheck_status,
            smoke_status=smoke_status,
        )
        return OperationalDeployResult(
            success=False,
            error=err,
            urls=registered_urls,
            supervisor_pid=supervisor_pid,
            steps=steps,
            healthcheck_status=healthcheck_status,
            smoke_status=smoke_status,
            route_registered=True,
            last_step=steps[-1]["name"] if steps else None,
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
        last_step=steps[-1]["name"] if steps else None,
    )


def apply_deploy_result_to_state(
    state: SandboxState, result: OperationalDeployResult
) -> SandboxState:
    """Merge a successful deploy result into sandbox state for the dashboard."""
    if not result.success:
        return apply_deploy_failure(state, result)
    return state.model_copy(
        update={
            "status": SandboxStatus.running,
            "lifecycle_phase": LifecyclePhase.running,
            "urls": result.urls,
            "supervisor_pid": result.supervisor_pid,
            "deployed_at": _now_iso(),
            "lifecycle_error": None,
            "last_step": result.last_step,
            "healthcheck_status": result.healthcheck_status,
            "smoke_status": result.smoke_status,
            "lifecycle_steps": result.steps,
        }
    )


def apply_deploy_failure(
    state: SandboxState, result: OperationalDeployResult
) -> SandboxState:
    """Persist failed lifecycle without removing the environment record."""
    return state.model_copy(
        update={
            "status": SandboxStatus.error,
            "lifecycle_phase": LifecyclePhase.failed,
            "lifecycle_error": result.error,
            "last_step": result.last_step,
            "healthcheck_status": result.healthcheck_status,
            "smoke_status": result.smoke_status,
            "lifecycle_steps": result.steps,
            "urls": {},
            "supervisor_pid": result.supervisor_pid,
        }
    )
