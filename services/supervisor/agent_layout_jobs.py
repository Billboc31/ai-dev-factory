"""Async job tracking for the install/update agent-layout task.

The agent-layout task (scan repo, call the LLM, write docs/, commit, push, open
a PR) can take minutes. To give the dashboard a live view (status + logs +
generated files) we run it in a background thread and persist a small job
record + a log file under the runtime root, mirroring the auto-fix proposer::

    Supervisor endpoint (POST /projects/{id}/install-agent-layout)
      -> background thread
        -> install_agent_layout(..., log_cb=append_log)
        -> persist_job (writes state.json under runtime_root)

Layout on disk::

    {runtime_root}/agent-layout/{project_id}/{job_id}/state.json
    {runtime_root}/agent-layout/{project_id}/{job_id}/job.log
"""
from __future__ import annotations

import datetime
import json
import uuid
from pathlib import Path


def _now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_job_id() -> str:
    return uuid.uuid4().hex[:12]


def _job_dir(runtime_root: Path, project_id: str, job_id: str) -> Path:
    return runtime_root / "agent-layout" / project_id / job_id


def job_log_path(runtime_root: Path, project_id: str, job_id: str) -> Path:
    return _job_dir(runtime_root, project_id, job_id) / "job.log"


def make_job(
    job_id: str,
    project_id: str,
    project_root: str,
    stack: str,
    exec_cmd: str,
    log_path: str,
) -> dict:
    return {
        "job_id": job_id,
        "project_id": project_id,
        "project_root": project_root,
        "stack": stack,
        "exec_cmd": exec_cmd,
        "status": "running",
        "started_at": _now_utc(),
        "finished_at": None,
        "branch": None,
        "result": None,
        "error": None,
        "log_path": log_path,
    }


def persist_job(project_id: str, job: dict, runtime_root: Path) -> None:
    """Write the job record to {runtime_root}/agent-layout/{project_id}/{job_id}/state.json."""
    path = _job_dir(runtime_root, project_id, job["job_id"]) / "state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(job, indent=2), encoding="utf-8")


def load_job(project_id: str, job_id: str, runtime_root: Path) -> dict | None:
    """Load a job by id. Returns None if not found or unreadable."""
    path = _job_dir(runtime_root, project_id, job_id) / "state.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_jobs(project_id: str, runtime_root: Path) -> list[dict]:
    """List all jobs for a project sorted by started_at ascending."""
    base = runtime_root / "agent-layout" / project_id
    if not base.exists():
        return []
    results: list[dict] = []
    for state_file in base.glob("*/state.json"):
        try:
            results.append(json.loads(state_file.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return sorted(results, key=lambda x: x.get("started_at", ""))


def latest_job(project_id: str, runtime_root: Path) -> dict | None:
    """Return the most recently started job for a project, or None."""
    jobs = list_jobs(project_id, runtime_root)
    return jobs[-1] if jobs else None


def append_log(log_path: Path, message: str) -> None:
    """Append a timestamped progress line to the job log (best-effort)."""
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(f"[{_now_utc()}] {message}\n")
            fh.flush()
    except OSError:
        pass


def read_log(log_path: Path, offset: int = 0) -> tuple[str, int]:
    """Return (text, new_offset) reading the log file from byte ``offset``.

    Enables incremental tailing from the dashboard without re-sending the whole
    log on every poll.
    """
    try:
        if not log_path.exists():
            return "", offset
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            fh.seek(offset)
            chunk = fh.read()
            return chunk, fh.tell()
    except OSError:
        return "", offset
