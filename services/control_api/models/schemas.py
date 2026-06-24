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
    runtime_root: str | None = None
    stack: str | None = None
    github_repo: str | None = None


class ProjectImportRequest(BaseModel):
    project_root: str
    project_id: str


class BootstrapResult(BaseModel):
    project_id: str
    project_root: str
    runtime_root: str
    stack: str
    runs_dir: str
    logs_dir: str
    state_dir: str
    worktrees_dir: str
    clones_dir: str = ""
    agent_layout_branch: str | None = None
    agent_layout_pr_url: str | None = None
    agent_layout_pr_number: int | None = None
    agent_layout_error: str | None = None


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
    degraded: bool = False


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
    smoke_status: Literal["skipped", "success", "failed"] = "skipped"


class DeployerStatus(BaseModel):
    state: Literal["idle", "running", "success", "failed"]
    profile_present: bool
    project_id: str
    started_at: str | None = None
    finished_at: str | None = None
    error: str | None = None
    last_step: str | None = None
    smoke_status: Literal["skipped", "success", "failed"] = "skipped"


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
    healthcheck_status: Literal["skipped", "success", "failed"] = "skipped"
    smoke_status: Literal["skipped", "success", "failed"] = "skipped"
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
    healthcheck_status: Literal["skipped", "success", "failed"] = "skipped"
    smoke_status: Literal["skipped", "success", "failed"] = "skipped"
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


class InstallAgentLayoutResult(BaseModel):
    branch: str | None = None
    pr_url: str | None = None
    pr_number: int | None = None
    docs_paths: list[str] = []
    docs_count: int = 0
    analysis_summary: str | None = None
    warnings: list[str] = []
    error: str | None = None


class AgentLayoutJobStart(BaseModel):
    ok: bool = True
    job_id: str


class AgentLayoutJobStatus(BaseModel):
    job_id: str
    project_id: str
    status: str
    started_at: str | None = None
    finished_at: str | None = None
    branch: str | None = None
    result: InstallAgentLayoutResult | None = None
    error: str | None = None


class AgentLayoutLogChunk(BaseModel):
    text: str = ""
    offset: int = 0
    status: str | None = None


class AgentLayoutFileEntry(BaseModel):
    status: str
    path: str


class AgentLayoutFileList(BaseModel):
    files: list[AgentLayoutFileEntry] = []
    docs_paths: list[str] = []
    warnings: list[str] = []
    branch: str | None = None


class AgentLayoutFileDetail(BaseModel):
    path: str
    content: str = ""
    diff: str = ""


class AgentLayoutStatus(BaseModel):
    layout_exists: bool = False
    ai_counts: dict[str, int] = {}
    docs_present: list[str] = []
    base_docs_present: int = 0
    base_docs_total: int = 0
    memory_files: dict[str, bool] = {}


class TicketIntelligence(BaseModel):
    ticket_id: str
    analysis_status: str
    difficulty_score: int | None = None
    difficulty_label: str | None = None
    risk_score: int | None = None
    risk_label: str | None = None
    complexity_factors: list[str] = []
    computed_signals_json: dict | None = None
    recommended_model: str | None = None
    recommended_model_reason: str | None = None
    estimated_input_tokens: int | None = None
    estimated_output_tokens: int | None = None
    estimated_cost_min: float | None = None
    estimated_cost_max: float | None = None
    cost_currency: str | None = None
    cost_estimate_status: str | None = None
    queue_rank: int | None = None
    queue_reason: str | None = None
    dependency_hints: list[str] = []
    parallel_safe_candidate: bool | None = None
    requires_human_plan_review: bool | None = None
    human_plan_review_reason: str | None = None
    requires_human_code_review: bool | None = None
    human_code_review_reason: str | None = None
    autonomous_execution_recommendation: str | None = None
    analysis_summary: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    failed_at: str | None = None
    failure_origin: str | None = None
    stage: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TicketIntelligenceQueued(BaseModel):
    ticket_id: str
    analysis_status: str


class TicketReadiness(BaseModel):
    ticket_id: str
    readiness_status: str
    ready_candidate: bool = False
    blocking_reasons: list[str] = []
    warnings: list[str] = []
    dependency_check_status: str | None = None
    approval_check_status: str | None = None
    context_freshness_status: str | None = None
    human_approval_required: bool | None = None
    human_approval_present: bool | None = None
    main_sha_when_evaluated: str | None = None
    evaluated_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TicketReadinessQueued(BaseModel):
    ticket_id: str
    readiness_status: str


class TicketApproval(BaseModel):
    id: int
    ticket_id: str
    approval_type: str
    approval_status: str
    approved_by: str | None = None
    approval_comment: str | None = None
    approved_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TicketApprovalHistory(BaseModel):
    ticket_id: str
    approvals: list[TicketApproval] = []


class ApprovalDecision(BaseModel):
    approved_by: str
    comment: str | None = None


class ProjectRule(BaseModel):
    rule_key: str
    enabled: bool
    configuration: dict = {}
    description: str | None = None
    default_enabled: bool | None = None
    default_configuration: dict | None = None


class ProjectRulesResponse(BaseModel):
    project_id: str
    rules: list[ProjectRule] = []


class ProjectRuleInput(BaseModel):
    rule_key: str
    enabled: bool
    configuration: dict = {}


class ProjectRulesUpdate(BaseModel):
    rules: list[ProjectRuleInput] | None = None
    action: Literal["reset_defaults"] | None = None


class RuleEvaluationEntry(BaseModel):
    rule_key: str
    reason: str


class RuleWarningEntry(BaseModel):
    rule_key: str
    message: str


class TicketRuleEvaluation(BaseModel):
    ticket_id: str
    project_id: str
    eligibility_status: str
    passed_rules: list[RuleEvaluationEntry] = []
    failed_rules: list[RuleEvaluationEntry] = []
    warnings: list[RuleWarningEntry] = []
    evaluated_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class TicketRuleEvaluationQueued(BaseModel):
    status: str
    ticket_id: str


class TicketExecutionEligibilityCheck(BaseModel):
    status: Literal["passed", "pending", "failed", "unknown"]
    detail: str | None = None
    unmet: list[str] | None = None


class TicketExecutionEligibility(BaseModel):
    ticket_id: str
    ready_to_take: bool
    status: Literal[
        "READY_TO_TAKE",
        "BLOCKED",
        "WAITING_HUMAN_ACTION",
        "DEPENDENCY_BLOCKED",
        "UNKNOWN",
    ]
    reason: str | None = None
    next_action: str | None = None
    blocking_step: Literal[
        "intelligence", "dependencies", "readiness", "rules", "approval"
    ] | None = None
    checks: dict[str, TicketExecutionEligibilityCheck] = {}
    evaluated_at: str | None = None


class DiagnosticCheck(BaseModel):
    key: str
    status: str
    message: str
    details: dict = {}


class DiagnosticRecommendedAction(BaseModel):
    action_key: str
    label: str
    risk: str
    reason: str


class TicketDiagnostics(BaseModel):
    ticket_id: str
    project_id: str | None = None
    diagnostic_status: str
    is_stuck: bool
    severity: str
    summary: str | None = None
    current_state: str | None = None
    last_known_step: str | None = None
    last_error: str | None = None
    checks: list[DiagnosticCheck] = []
    recommended_actions: list[DiagnosticRecommendedAction] = []
    generated_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class OperationDescriptor(BaseModel):
    operation_key: str
    label: str
    safety_level: Literal["low", "medium", "high", "destructive"]
    group: Literal["advisory", "approval", "recovery", "dangerous"]
    enabled: bool
    disabled_reason: str | None = None
    requires_reason: bool = False
    requires_typed_ticket_id: bool = False
    requires_double_confirmation: bool = False


class OperationListResponse(BaseModel):
    ticket_id: str
    operations: list[OperationDescriptor] = []


class OperationRequest(BaseModel):
    reason: str | None = None
    typed_ticket_id: str | None = None
    confirm: bool = False
    force: bool = False


class OperationResult(BaseModel):
    ticket_id: str
    operation_key: str
    status: Literal["completed", "rejected", "error"]
    message: str
    details: dict = {}
