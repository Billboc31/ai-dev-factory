from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class SandboxStatus(str, Enum):
    creating = "creating"
    running = "running"
    stopped = "stopped"
    error = "error"
    destroyed = "destroyed"


class SandboxState(BaseModel):
    id: str
    ticket_id: str
    project_root: str
    compose_project: str
    ports: dict[str, int]
    env_file: str
    status: SandboxStatus
    created_at: str
    slot: int
    supervisor_port: int = 0
    sandbox_runtime_root: str = ""
    supervisor_pid: int | None = None
    worktree_path: str | None = None
    job_type: str | None = None
    completed_at: str | None = None
    urls: dict[str, str] = {}
    requested_ref: str | None = None
    resolved_ref: str | None = None
    commit_sha: str | None = None
