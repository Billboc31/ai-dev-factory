from __future__ import annotations

from typing import Any
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"


class DaemonStatus(BaseModel):
    running: bool
    pid: int | None = None
    started_at: str | None = None
    last_heartbeat: str | None = None
    current_ticket: str | None = None


class DaemonActivity(BaseModel):
    lines: list[str]


class ActionResult(BaseModel):
    ok: bool
    message: str
    returncode: int | None = None
    stdout: str | None = None
    stderr: str | None = None


class TicketSummary(BaseModel):
    ticket_id: str
    state: str
    branch: str | None = None
    issue_number: int | None = None
    updated_at: str | None = None
    last_log: str | None = None


class TicketDetail(TicketSummary):
    pass


class IntakeRequest(BaseModel):
    issue_number: int


class IntakeStatusResponse(BaseModel):
    status: str
    detail: str | None = None


class ProjectInfo(BaseModel):
    name: str
    root: str
    tickets_count: int


class ProviderStatus(BaseModel):
    name: str
    available: bool
    detail: str | None = None
