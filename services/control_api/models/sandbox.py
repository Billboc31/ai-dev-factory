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
