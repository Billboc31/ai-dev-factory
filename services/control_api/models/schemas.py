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


class RetryInfo(BaseModel):
    failure_class: str | None = None
    retry_count: int = 0
    cooldown_until: str | None = None


class TicketSummary(BaseModel):
    ticket_id: str
    state: str
    branch: str | None = None
    issue_number: int | None = None
    updated_at: str | None = None
    last_log: str | None = None
    retry_info: RetryInfo | None = None


class TicketDetail(TicketSummary):
    pass


class TimelineStep(BaseModel):
    id: str
    label: str
    status: str  # pending | running | done | waiting_human | failed | skipped
    agent: str | None = None


class TimelineResponse(BaseModel):
    ticket_id: str
    current_state: str
    current_agent: str | None = None
    human_gate: bool = False
    last_event: str | None = None
    steps: list[TimelineStep]
    retry_info: RetryInfo | None = None
    last_error: str | None = None


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


class BoardItem(BaseModel):
    ticket_id: str | None = None
    issue_number: int | None = None
    title: str | None = None
    state: str | None = None
    branch: str | None = None
    worker_pid: int | None = None
    worker_cwd: str | None = None


class BoardColumn(BaseModel):
    id: str
    label: str
    items: list[BoardItem]


class BoardResponse(BaseModel):
    columns: list[BoardColumn]


class ProjectMapTicket(BaseModel):
    ticket_id: str | None = None
    issue_number: int | None = None
    title: str | None = None
    status: str
    depends_on: list[str] = []
    depends_on_issues: list[int] = []
    blocks: list[str] = []
    ambiguities: list[str] = []


class ProjectMapSummary(BaseModel):
    total: int
    done: int
    running: int
    waiting_human: int
    runnable: int
    blocked: int
    not_ingested: int = 0


class ProjectMapResponse(BaseModel):
    generated_at: str | None = None
    tickets: list[ProjectMapTicket] = []
    parallelizable_groups: list[list[str]] = []
    next_recommended: str | None = None
    cycles: list[list[str]] = []
    summary: ProjectMapSummary | None = None


class ProjectMapActivityEntry(BaseModel):
    timestamp: str
    total_issues: int
    runnable: list[str] = []
    blocked: list[str] = []
    parallelizable_groups: list[list[str]] = []
    next_recommended: str | None = None
    cycles: list[list[str]] = []
    ambiguities: list[Any] = []
    summary: Any = None


class ProjectMapActivityResponse(BaseModel):
    entries: list[ProjectMapActivityEntry] = []
