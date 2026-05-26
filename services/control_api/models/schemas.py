from __future__ import annotations

from typing import Any, Literal
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
    supervisor_available: bool | None = None
    supervisor_url: str | None = None
    last_exit_code: int | None = None
    last_exit_time: str | None = None
    last_error: str | None = None
    exit_unexpected: bool | None = None
    restart_count: int | None = None
    restart_policy: str | None = None


class DaemonStartRequest(BaseModel):
    restart_policy: str = "no-restart"


class DaemonActivity(BaseModel):
    lines: list[str]


class ActionResult(BaseModel):
    ok: bool
    message: str
    returncode: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    # Optional host-side launch command suggested when the API refuses to
    # start the daemon inside a Docker container. The dashboard surfaces
    # this string as a copy-paste block.
    host_command: str | None = None
    # Machine-readable error code (e.g. "supervisor_unreachable").
    error: str | None = None


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
    conflict_status: str | None = None
    conflicted_files: list[str] | None = None
    conflict_detected_at: str | None = None
    pre_conflict_state: str | None = None
    resolution_summary: str | None = None
    conflict_test_result: str | None = None


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


class AuditEvent(BaseModel):
    id: int
    event_type: str
    message: str
    metadata: dict | None = None
    created_at: str


class WorkerInfo(BaseModel):
    ticket_id: str
    pid: int | None = None
    worktree_path: str | None = None
    state: str | None = None


class RetryBlockedTicket(BaseModel):
    ticket_id: str
    failure_class: str | None = None
    retry_count: int = 0
    cooldown_until: str | None = None


class QueueEntry(BaseModel):
    issue_number: int | None = None
    title: str | None = None


class RuntimeStatus(BaseModel):
    daemon_online: bool
    workers: list[WorkerInfo] = []
    retry_blocked: list[RetryBlockedTicket] = []
    intake_queue: list[QueueEntry] = []
    last_action: str | None = None
    last_error: str | None = None


class DeployComponent(BaseModel):
    name: str
    type: Literal["docker", "host"]
    service: str | None = None
    command: str | None = None


class DeployHealthcheck(BaseModel):
    command: str
    timeout: int = 30
    retries: int = 3
    delay: int = 5


class DeployProfile(BaseModel):
    version: int
    project: str
    required_tools: list[str] = []
    components: list[DeployComponent] = []
    healthcheck: DeployHealthcheck | None = None
    undeploy: list[DeployComponent] = []
    cleanup: list[DeployComponent] = []


class ScanResult(BaseModel):
    docker_services: list[str] = []
    python_backend: bool = False
    node_frontend: bool = False
    required_tools: list[str] = []
    deploy_profile: DeployProfile | None = None


class DeployState(BaseModel):
    state: Literal["idle", "running", "success", "failed"] = "idle"
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    last_step: str | None = None


class DeployerStatus(BaseModel):
    state: Literal["idle", "running", "success", "failed"]
    profile_present: bool
    project_id: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    last_step: str | None = None


class DeployLogsResponse(BaseModel):
    lines: list[str]


# T134 — Schemas for the per-project deploy-validation pipeline.
#
# These models are intentionally namespaced with the ``SandboxValidation``
# prefix to keep them clearly distinct from the worker-isolation
# ``SandboxState`` / ``SandboxStatus`` enum & model defined in
# ``services.control_api.models.sandbox`` (T133/T136).
#
# Conceptually:
#   * ``SandboxState``       (models/sandbox.py)  → AI worker isolation
#   * ``SandboxValidation*`` (this module)         → deploy validation


class SandboxValidationStep(BaseModel):
    name: str
    status: Literal["skipped", "success", "failed"]
    exit_code: int | None = None
    started_at: str | None = None
    finished_at: str | None = None


class SandboxValidationState(BaseModel):
    state: Literal[
        "idle", "pending", "running", "success",
        "validating", "validated", "environment", "failed", "stopped", "cleaned",
    ] = "idle"
    mode: Literal["validation", "environment"] = "validation"
    sandbox_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    last_step: str | None = None
    steps: list[SandboxValidationStep] = []
    ports: dict[str, int] = {}
    worktree_path: str | None = None
    compose_project: str | None = None


class SandboxValidationStatus(BaseModel):
    state: Literal[
        "idle", "pending", "running", "success",
        "validating", "validated", "environment", "failed", "stopped", "cleaned",
    ]
    mode: Literal["validation", "environment"] = "validation"
    project_id: str
    sandbox_id: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    last_step: str | None = None
    steps: list[SandboxValidationStep] = []
    ports: dict[str, int] = {}
    worktree_path: str | None = None
    compose_project: str | None = None


class SandboxValidationLogsResponse(BaseModel):
    lines: list[str]


class AnalysisStatus(BaseModel):
    state: Literal["idle", "running", "success", "failed"] = "idle"
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    branch: str | None = None
    pr_url: str | None = None
    worktree_path: str | None = None


class ScriptsStatus(BaseModel):
    state: Literal["idle", "running", "success", "failed"] = "idle"
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    branch: str | None = None
    pr_url: str | None = None
