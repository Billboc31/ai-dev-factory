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
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..models.sandbox import EnvironmentMode, LifecyclePhase, SandboxState, SandboxStatus
from .infra_service_manager import resolve_proxy_routes_dir
from .proxy_manager import ProxyManager, build_sandbox_urls
from .proxy_network import sandbox_dns_aliases
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

    # Structured diagnostics block — always first so it's visible without scrolling.
    diag_lines = ["=== RUNTIME DIAGNOSTICS ==="]
    if state.project_root:
        diag_lines.append(f"project_root:         {state.project_root}")
    sandbox_root = state.sandbox_dir or str(sandbox_dir)
    diag_lines.append(f"sandbox_root:         {sandbox_root}")
    if state.sandbox_runtime_root:
        diag_lines.append(f"runtime_root:         {state.sandbox_runtime_root}")
    runtime_root_source = "override" if state.runtime_root else "auto"
    diag_lines.append(f"runtime_root_source:  {runtime_root_source}")
    if state.source_path:
        diag_lines.append(f"source_path:          {state.source_path}")

    validation_path = sandbox_dir / "runtime" / "validation.json"
    if validation_path.exists():
        try:
            v = json.loads(validation_path.read_text(encoding="utf-8", errors="replace"))
            diag_lines.append(f"healthcheck_status:   {v.get('healthcheck_status', 'unknown')}")
            diag_lines.append(f"smoke_status:         {v.get('smoke_status', 'unknown')}")
            if v.get("failing_step"):
                diag_lines.append(f"failing_step:         {v['failing_step']}")
            bd = v.get("backend_diagnostics") or {}
            if bd:
                diag_lines.append("--- proxy diagnostics ---")
                for k, val in bd.items():
                    diag_lines.append(f"  {k}: {val}")
        except (OSError, json.JSONDecodeError):
            pass

    sections.append("\n".join(diag_lines))

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


def _clone_fresh_source(
    project_root: Path,
    source_path: Path,
    ref: str | None,
    log: Callable[[str], None],
) -> tuple[bool, str | None, str | None]:
    """Clone project_root into source_path; checkout ref when given.

    Returns (ok, error_message, commit_sha).
    When ref is provided, aborts if the checked-out branch does not match.
    When ref is None, clones the default branch without a branch check.
    """
    log(f"\n--- fresh source clone ---\n")
    log(f"source: {project_root}\n")
    log(f"target: {source_path}\n")
    log(f"ref: {ref or '(default)'}\n")

    if source_path.exists():
        shutil.rmtree(source_path)

    clone_cmd = ["git", "clone"]
    if ref is not None:
        clone_cmd += ["--branch", ref]
    clone_cmd += [str(project_root), str(source_path)]

    result = subprocess.run(clone_cmd, capture_output=True, text=True, check=False)
    if result.stdout:
        log(result.stdout)
    if result.stderr:
        log(result.stderr)
    if result.returncode != 0:
        err = f"git clone failed: {result.stderr.strip()[:300]}"
        log(f"\n{err}\n")
        return False, err, None

    branch_result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True, check=False, cwd=str(source_path),
    )
    actual_branch = branch_result.stdout.strip()

    commit_result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=False, cwd=str(source_path),
    )
    commit_sha = commit_result.stdout.strip() or None

    log(f"pwd: {source_path}\n")
    log(f"git branch --show-current: {actual_branch}\n")
    log(f"git rev-parse --short HEAD: {commit_sha or '(unknown)'}\n")

    if ref is not None and actual_branch != ref:
        err = f"branch mismatch: expected {ref!r}, got {actual_branch!r}"
        log(f"\n{err}\n")
        return False, err, commit_sha

    log(f"\nsource ready: branch={actual_branch} commit={commit_sha}\n")
    return True, None, commit_sha


def _is_source_clone_valid(source_path: Path) -> bool:
    """Return True if the source clone is present and minimally usable."""
    return (
        source_path.is_dir()
        and (source_path / ".git").exists()
        and (source_path / ".ai-dev-factory" / "scripts").is_dir()
    )


def _rehydrate_source_clone(
    state: SandboxState,
    source_path: Path,
    project_root: Path,
    log_fn: Callable[[str], None],
) -> tuple[bool, str | None, str | None]:
    """Log rehydration diagnostics, then perform a fresh clone.

    Returns (ok, error_message, commit_sha).
    """
    log_fn(
        f"source clone missing or invalid\n"
        f"rehydrating sandbox source clone\n"
        f"repo={project_root}\n"
        f"branch={state.ref or '(default)'}\n"
        f"source_path={source_path}\n"
    )
    ok, err, sha = _clone_fresh_source(project_root, source_path, state.ref, log_fn)
    if ok:
        log_fn("sandbox source clone restored successfully\n")
    return ok, err, sha


def _resolve_runtime_root(
    state: SandboxState,
    sandbox_dir: Path,
) -> tuple[Path, str]:
    """Return (effective_sandbox_dir, runtime_root_source).

    When state.runtime_root is set, derives sandbox_dir from the override and
    validates path safety. Returns "override" as source; otherwise "auto".
    """
    if not state.runtime_root:
        return sandbox_dir, "auto"

    rt = Path(state.runtime_root)
    if not rt.is_absolute():
        raise ValueError(
            f"runtime_root must be an absolute path: {state.runtime_root!r}"
        )
    if any(part == ".." for part in rt.parts):
        raise ValueError(
            f"runtime_root must not contain '..': {state.runtime_root!r}"
        )

    new_sandbox_dir = (rt / state.id).resolve()
    try:
        new_sandbox_dir.relative_to(rt.resolve())
    except ValueError:
        raise ValueError(
            f"derived sandbox_dir {new_sandbox_dir} does not descend from "
            f"runtime_root {rt}"
        )
    new_sandbox_dir.mkdir(parents=True, exist_ok=True)
    return new_sandbox_dir, "override"


def deploy_operational_runtime(
    state: SandboxState,
    *,
    sandbox_dir: Path,
    mode: str = "environment",
    persist_state: Callable[[SandboxState], None] | None = None,
) -> OperationalDeployResult:
    """Run bootstrap → start scripts, supervisor, and Traefik for *state*.

    Pipeline progress is written to ``pipeline-state.json`` (not ``state.json``).
    Optional *persist_state* updates :class:`SandboxState` for live UI polling.
    A fresh git clone of ``state.project_root`` is always created under
    ``sandbox_dir/source/``; when ``state.ref`` is set the named branch is
    checked out and verified, otherwise the default branch is cloned.
    Scripts are consumed as committed in the clone — never from the host
    ai-dev-factory checkout.
    """
    rs = _import_run_sandbox()
    sandbox_dir, runtime_root_source = _resolve_runtime_root(state, sandbox_dir.resolve())
    log_path = sandbox_dir / "run.log"
    runtime_root = sandbox_dir / "runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    for subdir in ("state", "logs", "runs"):
        (runtime_root / subdir).mkdir(exist_ok=True)

    pipeline_state_path = sandbox_dir / "pipeline-state.json"
    project_root = Path(state.project_root).resolve()
    source_path = sandbox_dir / "source"

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
        "worktree_path": str(source_path),  # key kept for pipeline-state readers
        "source_path": str(source_path),
        "compose_project": state.compose_project,
        "project_root": str(project_root),
    }
    rs._append_log(log_path, f"\n=== operational deploy {state.id} mode={mode} ===\n")
    rs._append_log(log_path, (
        f"runtime_root={runtime_root}\n"
        f"runtime_root_source={runtime_root_source}\n"
        f"sandbox_root={sandbox_dir}\n"
        f"source_path={source_path}\n"
        f"project_root={project_root}\n"
    ))
    logger.info(
        "deploy %s: runtime_root=%s runtime_root_source=%s sandbox_root=%s source_path=%s project_root=%s",
        state.id, runtime_root, runtime_root_source, sandbox_dir, source_path, project_root,
    )
    _persist(LifecyclePhase.provisioning, last_step="supervisor")
    current[0] = current[0].model_copy(
        update={"effective_runtime_root": str(sandbox_dir.parent)}
    )
    if persist_state is not None:
        persist_state(current[0])

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
    _backend_diag: dict[str, str] = {}

    def _register_proxy_routes_after_compose() -> str | None:
        """Write route file and register sandbox backends with the proxy."""
        nonlocal registered_urls, route_registered, _backend_diag
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
        proxy_reachable = rs._wait_for_proxy_url(probe_url, log_path)
        _backend_diag = rs._log_proxy_backend_diagnostics(state.id, log_path)
        if _backend_diag.get("failure_type") == "dns_network":
            return (
                "DNS/network failure: backend is running but unreachable from Traefik"
                " — check shared ingress network"
            )
        if not proxy_reachable:
            return "reverse proxy route did not become reachable on host runtime"
        return None

    needs_rehydration = (
        not _is_source_clone_valid(source_path) or current[0].force_source_refresh
    )
    if needs_rehydration:
        clone_ok, clone_err, _ = _rehydrate_source_clone(
            current[0],
            source_path,
            project_root,
            lambda text: rs._append_log(log_path, text),
        )
    else:
        clone_ok, clone_err, _ = _clone_fresh_source(
            project_root,
            source_path,
            current[0].ref,
            lambda text: rs._append_log(log_path, text),
        )
    if not clone_ok:
        rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
        err = clone_err or "source clone failed"
        _persist(LifecyclePhase.failed, last_step="source-clone", lifecycle_error=err)
        return OperationalDeployResult(
            success=False,
            error=err,
            supervisor_pid=supervisor_pid,
            last_step="source-clone",
        )

    # Guard: source must resolve inside sandbox_dir to prevent path traversal.
    resolved_source = source_path.resolve()
    try:
        resolved_source.relative_to(sandbox_dir)
    except ValueError:
        err = (
            f"path validation failed: resolved source {resolved_source}"
            f" escapes sandbox {sandbox_dir}"
        )
        rs._append_log(log_path, f"\n{err}\n")
        rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
        _persist(LifecyclePhase.failed, last_step="path-validation", lifecycle_error=err)
        return OperationalDeployResult(
            success=False,
            error=err,
            supervisor_pid=supervisor_pid,
            last_step="path-validation",
        )

    for script_name in _SCRIPT_PHASE:
        script_path = resolved_source / ".ai-dev-factory" / "scripts" / script_name
        rs._append_log(log_path, f"resolved script path: {script_path}\n")

    def _on_step_start(script_name: str) -> None:
        phase = _SCRIPT_PHASE.get(script_name, LifecyclePhase.provisioning)
        _persist(phase, last_step=script_name)

    def _on_step_complete(script_name: str) -> bool | None:
        if script_name != "start.sh":
            return None
        route_err = _register_proxy_routes_after_compose()
        return route_err is None

    # Pre-flight: SANDBOX_ID must be non-empty and consistent with state.id.
    # An empty or mismatched value causes docker-compose to register aliases
    # under the wrong slug (e.g. sandbox-default-api instead of sandbox-main-api),
    # making all Traefik backend targets unresolvable → 502.
    sandbox_id_env = extra_env.get("SANDBOX_ID", "")
    if not sandbox_id_env:
        msg = (
            f"deploy aborted: SANDBOX_ID is empty for environment '{state.id}'"
            " — ensure SANDBOX_ID is propagated before deploying a named environment"
        )
        rs._append_log(log_path, f"\n{msg}\n")
        rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
        _persist(LifecyclePhase.failed, last_step="preflight", lifecycle_error=msg)
        return OperationalDeployResult(success=False, error=msg, last_step="preflight")
    if sandbox_id_env != state.id:
        expected = sandbox_dns_aliases(state.id)
        msg = (
            f"deploy aborted: SANDBOX_ID mismatch —"
            f" extra_env has '{sandbox_id_env}' but state.id is '{state.id}';"
            f" compose aliases would target {expected} while routes point elsewhere"
        )
        rs._append_log(log_path, f"\n{msg}\n")
        rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
        _persist(LifecyclePhase.failed, last_step="preflight", lifecycle_error=msg)
        return OperationalDeployResult(success=False, error=msg, last_step="preflight")

    success, script_error, steps, _hc_diag = rs._run_scripts(
        source_path,
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
            source_path, log_path, extra_env
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
        backend_diagnostics=_backend_diag or None,
        healthcheck_diagnostics=_hc_diag,
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
        rs._run_stop_script(source_path, log_path, extra_env)
        rs._stop_sandbox_supervisor(supervisor_proc, runtime_root, log_path)
        ProxyManager(routes_dir=routes_dir, auto_ensure_infra=False).unregister(
            state.id,
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
