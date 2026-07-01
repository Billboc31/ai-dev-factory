"""Daemon lifecycle management via PID file at runs/daemon.pid."""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import httpx

from ..models.schemas import ActionResult, DaemonStatus, QueueEntry, RetryBlockedTicket, RuntimeStatus, WorkerInfo
from .runtime_resolver import resolve_logs_dir, resolve_runs_dir, resolve_state_dir, resolve_worktrees_dir


logger = logging.getLogger("control-api")

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
_RUN_DAEMON = _TOOLS_DIR / "run_daemon.py"

_PID_FILENAME = "daemon.pid"
_LOG_FILENAME = "daemon.log"
_TICKET_RE = re.compile(r"^T\d{3,}$")


def _pid_path(project_root: Path) -> Path:
    return resolve_runs_dir(project_root) / _PID_FILENAME


def _log_path(project_root: Path) -> Path:
    return resolve_logs_dir(project_root) / _LOG_FILENAME


def _read_pid_file(project_root: Path) -> dict | None:
    path = _pid_path(project_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_pid_file(project_root: Path, pid: int, started_at: str) -> None:
    path = _pid_path(project_root)
    path.write_text(
        json.dumps({"pid": pid, "started_at": started_at}),
        encoding="utf-8",
    )


def _remove_pid_file(project_root: Path) -> None:
    try:
        _pid_path(project_root).unlink()
    except OSError:
        pass


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ── Docker detection / host-launcher escape hatch ─────────────────────────────

def _is_running_in_docker() -> bool:
    """Return True when the API process is running inside a Docker container.

    Detection order (first match wins):
      1. explicit override ``AI_DEV_FACTORY_API_IN_DOCKER=1`` (Compose file
         sets this and is the trusted signal),
      2. ``/.dockerenv`` file exists (Docker default sentinel),
      3. ``/proc/1/cgroup`` mentions ``docker`` or ``containerd`` (Linux fallback).
    """
    if os.environ.get("AI_DEV_FACTORY_API_IN_DOCKER", "").lower() in {"1", "true", "yes"}:
        return True
    if Path("/.dockerenv").exists():
        return True
    try:
        cgroup = Path("/proc/1/cgroup").read_text(encoding="utf-8", errors="ignore")
        if "docker" in cgroup or "containerd" in cgroup:
            return True
    except OSError:
        pass
    return False


def _expand_user(path_str: str) -> str:
    """``Path.expanduser`` but resilient to non-string input."""
    try:
        return str(Path(path_str).expanduser())
    except (TypeError, ValueError):
        return path_str


def _recommended_host_command(
    project_root: Path,
    exec_cmd: str,
    repo_slug: str | None = None,
) -> str:
    """Build the canonical multi-line host command for the dashboard to copy.

    The command is intentionally one operator-friendly chain that:
      - ``cd``s into the host clone (preferring ``AI_DEV_FACTORY_PROJECT_ROOT``
        if set, otherwise a sensible default under the user's runtime root),
      - activates the host venv,
      - exports ``AI_DEV_FACTORY_RUNTIME_ROOT``,
      - invokes ``tools/agent_runner/run_daemon.py`` with the full set of
        flags ``daemon_manager.start`` uses (``--poll-issues``,
        ``--auto-commit``, ``--auto-push``, ``--auto-include-code``).
    Operators can paste it directly into a host terminal or wrap it in
    ``ssh host -- '…'`` and feed that back via
    ``AI_DEV_FACTORY_HOST_DAEMON_COMMAND``.
    """
    runtime_root = os.environ.get(
        "AI_DEV_FACTORY_RUNTIME_ROOT", "~/runtime/ai-dev-factory"
    )
    host_clone = os.environ.get(
        "AI_DEV_FACTORY_PROJECT_ROOT",
        f"{runtime_root}/clones/ai-dev-factory",
    )
    host_clone = _expand_user(host_clone)
    runtime_root_display = _expand_user(runtime_root)
    issue_repo = repo_slug or os.environ.get("AI_DEV_FACTORY_ISSUE_REPO", "<owner>/<repo>")

    # Poll interval is resolved per-cycle from the GITHUB_POLL_INTERVAL_SECONDS
    # runtime setting so admins can change it from the settings UI without
    # editing this command. Pass an explicit ``--interval N`` to pin the value.
    return (
        f"cd {host_clone} && "
        f"source .venv/bin/activate && "
        f"export AI_DEV_FACTORY_RUNTIME_ROOT={runtime_root_display} && "
        f"python tools/agent_runner/run_daemon.py "
        f'--exec-cmd "{exec_cmd}" '
        f"--poll-issues "
        f"--issue-repo {issue_repo} "
        f"--auto-commit "
        f"--auto-push "
        f"--auto-include-code"
    )


def _host_daemon_command_env() -> str | None:
    cmd = os.environ.get("AI_DEV_FACTORY_HOST_DAEMON_COMMAND")
    if cmd and cmd.strip():
        return cmd
    return None


# ── Supervisor delegation ─────────────────────────────────────────────────────

def _supervisor_url() -> str | None:
    url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL")
    return url.rstrip("/") if url and url.strip() else None


def _supervisor_start_command() -> str:
    """Return the host command to launch the supervisor itself."""
    runtime_root = os.environ.get(
        "AI_DEV_FACTORY_RUNTIME_ROOT", "~/runtime/ai-dev-factory"
    )
    host_clone = os.environ.get(
        "AI_DEV_FACTORY_PROJECT_ROOT",
        f"{runtime_root}/clones/ai-dev-factory",
    )
    host_clone = _expand_user(host_clone)
    return f"cd {host_clone} && bash deploy/start_supervisor.sh"


def _call_supervisor(
    method: str,
    path: str,
    json_body: dict | None = None,
    timeout: float = 2.0,
) -> tuple[dict | None, str | None]:
    """Call the supervisor API. Returns (data, error_code)."""
    url = _supervisor_url()
    if url is None:
        return None, "no_supervisor_url"
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


def _last_heartbeat(project_root: Path, project_runtime_root: Path | None = None) -> str | None:
    if project_runtime_root is not None:
        path = project_runtime_root / "logs" / _LOG_FILENAME
    else:
        path = _log_path(project_root)
    if not path.exists():
        return None
    try:
        mtime = path.stat().st_mtime
        return datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return None


def _current_ticket(project_root: Path, project_runtime_root: Path | None = None) -> str | None:
    runs = resolve_runs_dir(project_root, project_runtime_root=project_runtime_root)
    if not runs.exists():
        return None
    for ticket_dir in sorted(runs.iterdir(), reverse=True):
        if not _TICKET_RE.match(ticket_dir.name):
            continue
        state_file = ticket_dir / "state.json"
        if not state_file.exists():
            continue
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            if "RUNNING" in (data.get("state") or ""):
                return ticket_dir.name
        except (json.JSONDecodeError, OSError):
            continue
    return None


def get_status(project_root: Path, project_id: str | None = None, project_runtime_root: Path | None = None) -> DaemonStatus:
    if _supervisor_url():
        status_path = f"/projects/{project_id}/daemon/status" if project_id else "/daemon/status"
        sup_data, error = _call_supervisor("GET", status_path)
        if error is None and sup_data:
            return DaemonStatus(
                running=sup_data.get("running", False),
                pid=sup_data.get("pid"),
                started_at=sup_data.get("started_at"),
                last_heartbeat=_last_heartbeat(project_root, project_runtime_root),
                current_ticket=_current_ticket(project_root, project_runtime_root),
                last_exit_code=sup_data.get("last_exit_code"),
                last_exit_time=sup_data.get("last_exit_time"),
                last_error=sup_data.get("last_error"),
                exit_unexpected=sup_data.get("exit_unexpected"),
                restart_count=sup_data.get("restart_count"),
                restart_policy=sup_data.get("restart_policy"),
            )
        # Supervisor unreachable — fall back to local check (may not work in
        # Docker since os.kill cannot reach host PIDs, but returns False safely)

    data = _read_pid_file(project_root)
    if data is None:
        return DaemonStatus(running=False)
    pid = data.get("pid")
    if not isinstance(pid, int):
        _remove_pid_file(project_root)
        return DaemonStatus(running=False)
    if not _is_alive(pid):
        _remove_pid_file(project_root)
        return DaemonStatus(running=False)
    return DaemonStatus(
        running=True,
        pid=pid,
        started_at=data.get("started_at"),
        last_heartbeat=_last_heartbeat(project_root, project_runtime_root),
        current_ticket=_current_ticket(project_root, project_runtime_root),
    )


def get_activity(project_root: Path, lines: int = 50, project_runtime_root: Path | None = None) -> list[str]:
    if project_runtime_root is not None:
        path = project_runtime_root / "logs" / _LOG_FILENAME
    else:
        path = _log_path(project_root)
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        all_lines = [ln for ln in text.splitlines() if ln.strip()]
        return all_lines[-lines:]
    except OSError:
        return []


def check_environment(project_root: Path, project_runtime_root: Path | None = None) -> tuple[bool, list[str], dict[str, str]]:
    """Return ``(ok, errors, facts)`` describing the canonical daemon env.

    The dashboard daemon must run in the same environment as a host-side
    manual daemon. This helper records every fact and refuses anything that
    is *quietly* broken — silent degraded mode is precisely what broke the
    T123/T124 dashboard launch (no ``gh``, no ``.git``, wrong ``cwd``).

    Facts (always populated, even on failure):
      - project_root: absolute path the daemon will be spawned in
      - cwd: same as project_root, kept for clarity in logs
      - runs_dir / worktrees_dir / logs_dir: canonical resolved locations
      - runtime_root: ``AI_DEV_FACTORY_RUNTIME_ROOT`` (or "<unset>")
      - gh_path: absolute path to ``gh`` if found, "<missing>" otherwise
      - git_path: absolute path to ``git``
      - python: ``sys.executable``

    Errors (the daemon refuses to start when any are present):
      - missing ``gh`` CLI in PATH
      - missing ``git`` CLI in PATH
      - ``project_root`` is not a directory or not a git repo (no ``.git``)
      - ``runs_dir`` cannot be created/written to
    """
    errors: list[str] = []
    facts: dict[str, str] = {
        "project_root": str(project_root),
        "cwd": str(project_root),
        "runs_dir": str(resolve_runs_dir(project_root, project_runtime_root=project_runtime_root)),
        "worktrees_dir": str(resolve_worktrees_dir(project_root, project_runtime_root=project_runtime_root)),
        "logs_dir": str(resolve_logs_dir(project_root, project_runtime_root=project_runtime_root)),
        "runtime_root": os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT", "<unset>"),
        "python": sys.executable,
        "gh_path": shutil.which("gh") or "<missing>",
        "git_path": shutil.which("git") or "<missing>",
    }

    if facts["gh_path"] == "<missing>":
        errors.append(
            "gh CLI not found in PATH — daemon cannot poll issues, "
            "create or update PRs. Install gh or ensure the API process "
            "PATH includes the host gh binary."
        )
    if facts["git_path"] == "<missing>":
        errors.append("git not found in PATH — daemon cannot run.")

    if not project_root.is_dir():
        errors.append(f"project_root is not a directory: {project_root}")
    elif not (project_root / ".git").exists():
        # Could be a bare worktree dir; check `git rev-parse` to be safe.
        try:
            result = subprocess.run(
                ["git", "-C", str(project_root), "rev-parse", "--git-dir"],
                capture_output=True, text=True, check=False, timeout=5,
            )
            if result.returncode != 0:
                errors.append(
                    f"project_root has no .git and is not a git working tree: "
                    f"{project_root} — daemon needs git access for worktree sync."
                )
        except (OSError, subprocess.SubprocessError) as exc:
            errors.append(f"git rev-parse failed at {project_root}: {exc}")

    runs_dir = Path(facts["runs_dir"])
    try:
        runs_dir.mkdir(parents=True, exist_ok=True)
        # Touch a sentinel to confirm writability
        sentinel = runs_dir / ".preflight-write-check"
        sentinel.write_text("ok", encoding="utf-8")
        sentinel.unlink()
    except OSError as exc:
        errors.append(f"runs_dir not writable: {runs_dir} — {exc}")

    return (not errors), errors, facts


def _format_environment_banner(facts: dict[str, str]) -> str:
    """Multiline banner suitable for writing into ``daemon.log`` before spawn."""
    lines = ["daemon environment:"]
    for key in (
        "project_root", "cwd", "runtime_root",
        "runs_dir", "worktrees_dir", "logs_dir",
        "python", "git_path", "gh_path",
        "in_docker",
    ):
        if key in facts:
            lines.append(f"  {key}={facts.get(key, '<unknown>')}")
    return "\n".join(lines)


def _refuse_with_log(project_root: Path, message: str, errors: list[str], facts: dict[str, str]) -> None:
    """Persist a startup refusal to ``daemon.log`` for dashboard visibility."""
    try:
        log = _log_path(project_root)
        log.parent.mkdir(parents=True, exist_ok=True)
        with open(log, "a", encoding="utf-8") as log_fh:
            log_fh.write(f"[{datetime.datetime.now(datetime.timezone.utc).isoformat()}] startup refused\n")
            log_fh.write(_format_environment_banner(facts) + "\n")
            log_fh.write(f"  reason: {message}\n")
            for err in errors:
                log_fh.write(f"  ERROR: {err}\n")
    except OSError:
        pass


def _start_via_host_command(project_root: Path, host_cmd: str) -> ActionResult:
    """Execute ``AI_DEV_FACTORY_HOST_DAEMON_COMMAND`` (typically an SSH wrapper).

    The shell is responsible for the full setup — venv activation, env vars,
    ``cd`` into the host clone, …. We pass the command verbatim through
    ``shell=True`` and do not write a PID file ourselves: the host daemon
    writes its own ``runs/daemon.pid`` from inside the canonical runtime
    root, and the dashboard discovers it on the next poll.
    """
    log = _log_path(project_root)
    log.parent.mkdir(parents=True, exist_ok=True)
    started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        with open(log, "a", encoding="utf-8") as log_fh:
            log_fh.write(
                f"[{started_at}] launching daemon via "
                f"AI_DEV_FACTORY_HOST_DAEMON_COMMAND\n"
                f"  command={host_cmd}\n"
            )
            log_fh.flush()
            # ``shell=True`` is intentional: the configured command is a free
            # shell snippet (typically `ssh host -- 'cd ... && python ...'`).
            # Operators configuring this env var accept the responsibility.
            proc = subprocess.Popen(
                host_cmd,
                shell=True,
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,
                env=env,
            )
        logger.info("api: launched host daemon wrapper pid=%d", proc.pid)
        return ActionResult(
            ok=True,
            message=(
                "host daemon launcher started (pid="
                f"{proc.pid}). PID file is written by the host process."
            ),
        )
    except OSError as exc:
        return ActionResult(
            ok=False,
            message=f"host daemon launcher failed: {exc}",
        )


def start(project_root: Path, exec_cmd: str, restart_policy: str = "no-restart", project_id: str | None = None, project_runtime_root: Path | None = None) -> ActionResult:
    """Start the daemon — host-side, never inside Docker.

    Four paths:

    0. **Supervisor configured** (``AI_DEV_FACTORY_SUPERVISOR_URL``): delegate
       to the host supervisor HTTP API. If unreachable, return a structured
       error with ``error="supervisor_unreachable"`` and a copy-paste
       ``host_command`` to launch the supervisor.

    1. **Host launcher configured** (``AI_DEV_FACTORY_HOST_DAEMON_COMMAND``):
       run the configured shell command verbatim (typically ``ssh host -- …``).
       This is the only mode that works when the API is in Docker.

    2. **API in Docker, no host launcher**: refuse with a clear message and
       a copy-paste ``host_command`` field. Do NOT write a PID file.

    3. **API on host**: existing preflight + Popen flow.
    """
    logger.info("api: daemon start requested")
    status = get_status(project_root, project_id=project_id, project_runtime_root=project_runtime_root)
    if status.running:
        return ActionResult(ok=False, message=f"daemon already running (pid={status.pid})")

    # ── path 0: supervisor delegation ─────────────────────────────────────
    if _supervisor_url():
        start_path = f"/projects/{project_id}/daemon/start" if project_id else "/daemon/start"
        data, error = _call_supervisor("POST", start_path, {"exec_cmd": exec_cmd, "restart_policy": restart_policy})
        if error == "supervisor_unreachable":
            logger.warning("api: supervisor unreachable at %s", _supervisor_url())
            return ActionResult(
                ok=False,
                message=(
                    "Supervisor unreachable. Start it on the host first: "
                    "bash deploy/start_supervisor.sh"
                ),
                error="supervisor_unreachable",
                host_command=_supervisor_start_command(),
            )
        if data:
            if data.get("ok"):
                logger.info("api: supervisor started daemon pid=%s", data.get("pid"))
                return ActionResult(
                    ok=True,
                    message=f"supervisor started daemon (pid={data.get('pid')})",
                )
            return ActionResult(
                ok=False,
                message=data.get("error") or "supervisor start failed",
                error=data.get("error"),
            )

    host_cmd = _host_daemon_command_env()
    in_docker = _is_running_in_docker()

    # ── path 1: explicit host launcher (works from Docker too) ────────────
    if host_cmd:
        logger.info("api: AI_DEV_FACTORY_HOST_DAEMON_COMMAND set, delegating to host launcher")
        return _start_via_host_command(project_root, host_cmd)

    # ── path 2: Docker without a host launcher → hard refusal ─────────────
    if in_docker:
        recommended = _recommended_host_command(project_root, exec_cmd)
        message = (
            "Daemon cannot start inside Docker. Run it on the host (where "
            "gh, claude and the git worktrees live), or configure "
            "AI_DEV_FACTORY_HOST_DAEMON_COMMAND with a shell command that "
            "starts the daemon on the host (e.g. an ssh wrapper)."
        )
        facts = {
            "project_root": str(project_root),
            "cwd": str(project_root),
            "runs_dir": str(resolve_runs_dir(project_root)),
            "worktrees_dir": str(resolve_worktrees_dir(project_root)),
            "logs_dir": str(resolve_logs_dir(project_root)),
            "runtime_root": os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT", "<unset>"),
            "python": sys.executable,
            "gh_path": shutil.which("gh") or "<missing>",
            "git_path": shutil.which("git") or "<missing>",
            "in_docker": "true",
        }
        _refuse_with_log(
            project_root,
            message,
            errors=["API runs in Docker — daemon must run on host."],
            facts=facts,
        )
        logger.warning("api: daemon start refused — running in Docker, no host launcher")
        return ActionResult(
            ok=False,
            message=message,
            host_command=recommended,
        )

    # ── path 3: API runs on the host — preflight + Popen ──────────────────
    ok, errors, facts = check_environment(project_root)
    if not ok:
        msg = "daemon refused to start — invalid environment:\n  " + "\n  ".join(errors)
        _refuse_with_log(project_root, msg, errors, facts)
        logger.warning("api: daemon start refused — %s", errors)
        return ActionResult(ok=False, message=msg)

    started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log = _log_path(project_root)
    log.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(_RUN_DAEMON),
        "--exec-cmd",
        exec_cmd,
        "--poll-issues",
        "--issue-label",
        "ai-ready",
        "--auto-commit",
        "--auto-push",
        # ``--auto-include-code`` is required for auto-commit to stage real
        # implementation files (apps/, services/, …) alongside the workflow
        # artifacts. Without it the coder leaves the worktree dirty and the
        # next `git pull --rebase` fails.
        "--auto-include-code",
        "--worktrees-dir",
        facts["worktrees_dir"],
    ]

    try:
        # Suppress .pyc generation for the entire daemon process tree so the
        # workflow does not pollute worktrees with __pycache__ entries that
        # would later show up as dirty paths and block git pull --rebase.
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        with open(log, "a", encoding="utf-8") as log_fh:
            # Banner BEFORE Popen so any spawn failure is still observable.
            log_fh.write(
                f"[{started_at}] preparing to spawn daemon\n"
                + _format_environment_banner(facts) + "\n"
                f"  command={' '.join(cmd)}\n"
            )
            log_fh.flush()
            proc = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,
                env=env,
            )
        _write_pid_file(project_root, proc.pid, started_at)
        logger.info("api: daemon started pid=%d", proc.pid)
        return ActionResult(ok=True, message=f"daemon started (pid={proc.pid})")
    except OSError as exc:
        # Popen failure (rare: usually permission / fd / missing python).
        # No PID file is written — dashboard status remains accurate.
        return ActionResult(ok=False, message=f"daemon spawn failed: {exc}")


def stop(project_root: Path, project_id: str | None = None, project_runtime_root: Path | None = None) -> ActionResult:
    logger.info("api: daemon stop requested")

    if _supervisor_url():
        stop_path = f"/projects/{project_id}/daemon/stop" if project_id else "/daemon/stop"
        data, error = _call_supervisor("POST", stop_path)
        if error == "supervisor_unreachable":
            logger.warning("api: supervisor unreachable at %s", _supervisor_url())
            return ActionResult(
                ok=False,
                message="Supervisor unreachable — cannot stop daemon remotely",
                error="supervisor_unreachable",
            )
        if data:
            if data.get("ok"):
                logger.info("api: daemon stopped via supervisor")
                return ActionResult(ok=True, message="daemon stopped via supervisor")
            return ActionResult(
                ok=False,
                message=data.get("error") or "supervisor stop failed",
                error=data.get("error"),
            )

    status = get_status(project_root)
    if not status.running or status.pid is None:
        return ActionResult(ok=False, message="daemon is not running")
    try:
        os.kill(status.pid, signal.SIGTERM)
        _remove_pid_file(project_root)
        logger.info("api: daemon stopped pid=%d", status.pid)
        return ActionResult(ok=True, message=f"daemon stopped (pid={status.pid})")
    except OSError as exc:
        return ActionResult(ok=False, message=str(exc))


def restart(project_root: Path, exec_cmd: str, restart_policy: str = "no-restart", project_id: str | None = None, project_runtime_root: Path | None = None) -> ActionResult:
    logger.info("api: daemon restart requested")
    stop_result = stop(project_root, project_id=project_id, project_runtime_root=project_runtime_root)
    if not stop_result.ok and "not running" not in stop_result.message:
        return stop_result
    return start(project_root, exec_cmd, restart_policy, project_id=project_id, project_runtime_root=project_runtime_root)


def get_workers(project_root: Path, project_runtime_root: Path | None = None) -> list[WorkerInfo]:
    runs_dir = resolve_runs_dir(project_root, project_runtime_root=project_runtime_root)
    state_dir = resolve_state_dir(project_root, project_runtime_root=project_runtime_root)
    workers_path = state_dir / "workers.json"
    if not workers_path.exists():
        workers_path = runs_dir / "workers.json"
    try:
        raw: dict = json.loads(workers_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    result = []
    for ticket_id, info in raw.items():
        wt_path = info.get("worktree_path")
        state = None
        for candidate in [
            Path(wt_path) / "runs" / ticket_id / "state.json" if wt_path else None,
            runs_dir / ticket_id / "state.json",
        ]:
            if candidate and candidate.exists():
                try:
                    state = json.loads(candidate.read_text(encoding="utf-8")).get("state")
                    break
                except (json.JSONDecodeError, OSError):
                    pass
        result.append(WorkerInfo(
            ticket_id=ticket_id,
            pid=info.get("pid"),
            worktree_path=wt_path,
            state=state,
        ))
    return result


def get_retry_blocked(project_root: Path, project_runtime_root: Path | None = None) -> list[RetryBlockedTicket]:
    runs_dir = resolve_runs_dir(project_root, project_runtime_root=project_runtime_root)
    if not runs_dir.exists():
        return []
    result = []
    for ticket_dir in sorted(runs_dir.iterdir()):
        if not _TICKET_RE.match(ticket_dir.name):
            continue
        retry_file = ticket_dir / "retry-state.json"
        if not retry_file.exists():
            continue
        try:
            data = json.loads(retry_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        retry_count = data.get("retry_count", 0)
        cooldown_until = data.get("cooldown_until")
        if retry_count == 0 and not cooldown_until:
            continue
        result.append(RetryBlockedTicket(
            ticket_id=ticket_dir.name,
            failure_class=data.get("failure_class"),
            retry_count=retry_count,
            cooldown_until=cooldown_until,
        ))
    return result


def get_intake_queue(project_root: Path, project_runtime_root: Path | None = None) -> list[QueueEntry]:
    runs_dir = resolve_runs_dir(project_root, project_runtime_root=project_runtime_root)
    if not runs_dir.exists():
        return []
    state_dir = resolve_state_dir(project_root, project_runtime_root=project_runtime_root)
    workers_path = state_dir / "workers.json"
    if not workers_path.exists():
        workers_path = runs_dir / "workers.json"
    try:
        active_tickets: set[str] = set(json.loads(workers_path.read_text(encoding="utf-8")).keys())
    except (json.JSONDecodeError, OSError):
        active_tickets = set()
    result = []
    for ticket_dir in sorted(runs_dir.iterdir()):
        if not _TICKET_RE.match(ticket_dir.name):
            continue
        if ticket_dir.name in active_tickets:
            continue
        state_file = ticket_dir / "state.json"
        if not state_file.exists():
            continue
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        state = data.get("state", "")
        if data.get("daemon_archived") or data.get("issue_closed"):
            continue
        if "RUNNING" in state:
            continue
        if any(s in state for s in ("DONE", "MERGED", "CLOSED", "ARCHIVED")):
            continue
        result.append(QueueEntry(
            issue_number=data.get("issue_number"),
            title=data.get("title") or ticket_dir.name,
        ))
    return result


def get_last_error(project_root: Path, project_runtime_root: Path | None = None) -> str | None:
    if project_runtime_root is not None:
        path = project_runtime_root / "logs" / _LOG_FILENAME
    else:
        path = _log_path(project_root)
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        for line in reversed(text.splitlines()):
            if line.strip() and any(kw in line.lower() for kw in ("error", "exception", "failed", "traceback")):
                return line.strip()
        return None
    except OSError:
        return None


def get_runtime_status(project_root: Path, project_id: str | None = None, project_runtime_root: Path | None = None) -> RuntimeStatus:
    status = get_status(project_root, project_id=project_id, project_runtime_root=project_runtime_root)
    return RuntimeStatus(
        daemon_online=status.running,
        workers=get_workers(project_root, project_runtime_root=project_runtime_root),
        retry_blocked=get_retry_blocked(project_root, project_runtime_root=project_runtime_root),
        intake_queue=get_intake_queue(project_root, project_runtime_root=project_runtime_root),
        last_action=_last_heartbeat(project_root, project_runtime_root),
        last_error=get_last_error(project_root, project_runtime_root=project_runtime_root),
    )


def sync_main(project_root: Path) -> ActionResult:
    logger.info("api: sync-main requested")
    try:
        result = subprocess.run(
            ["git", "fetch", "origin", "main"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return ActionResult(ok=True, message="Fetched origin/main successfully")
        return ActionResult(ok=False, message=result.stderr.strip() or "git fetch failed")
    except subprocess.TimeoutExpired:
        return ActionResult(ok=False, message="git fetch timed out")
    except OSError as exc:
        return ActionResult(ok=False, message=str(exc))
