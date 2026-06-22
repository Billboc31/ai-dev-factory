"""Execution Rules routes — project rules + per-ticket rule evaluation.

Endpoints:
    GET  /projects/{project_id}/rules
    PUT  /projects/{project_id}/rules
    GET  /tickets/{ticket_id}/rule-evaluation
    POST /tickets/{ticket_id}/evaluate-rules

The engine itself is advisory: scheduler and execution pipeline are untouched.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from ..models.schemas import (
    ProjectRule,
    ProjectRulesResponse,
    ProjectRulesUpdate,
    RuleEvaluationEntry,
    RuleWarningEntry,
    TicketRuleEvaluation,
    TicketRuleEvaluationQueued,
)
from ..services.artifact_reader import get_ticket

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import execution_rules_engine as _engine  # noqa: E402
import runtime_db  # noqa: E402

logger = logging.getLogger("control-api")

project_router = APIRouter(prefix="/projects", tags=["rules"])
ticket_router = APIRouter(prefix="/tickets", tags=["rules"])
project_ticket_router = APIRouter(prefix="/projects", tags=["rules"])


def _root(request: Request) -> Path:
    return request.app.state.project_root


def _db_path(request: Request):
    db = getattr(request.app.state, "db_path", None)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")
    return db


def _worktrees_dir(request: Request) -> Path | None:
    return getattr(request.app.state, "worktrees_dir", None)


def _require_ticket(request: Request, ticket_id: str) -> None:
    ticket = get_ticket(_root(request), ticket_id, worktrees_dir=_worktrees_dir(request))
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")


def _validate_rule_input(rule_key: str, configuration: dict) -> None:
    spec = _engine.RULE_REGISTRY.get(rule_key)
    if spec is None:
        raise HTTPException(
            status_code=422,
            detail=f"unknown rule_key '{rule_key}'",
        )
    if rule_key == "max_estimated_cost_usd":
        val = configuration.get("max_cost_usd")
        if val is not None:
            try:
                if float(val) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=422,
                    detail="max_cost_usd must be a non-negative number",
                )
    if rule_key == "max_difficulty":
        val = configuration.get("max_difficulty")
        if val is not None:
            try:
                if int(val) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=422,
                    detail="max_difficulty must be a non-negative integer",
                )


def _effective_rules_to_response(project_id: str, effective: list[dict]) -> ProjectRulesResponse:
    rules = []
    for rule in effective:
        spec = _engine.RULE_REGISTRY.get(rule["rule_key"])
        rules.append(
            ProjectRule(
                rule_key=rule["rule_key"],
                enabled=bool(rule.get("enabled")),
                configuration=rule.get("configuration") or {},
                description=spec.description if spec else None,
                default_enabled=spec.default_enabled if spec else None,
                default_configuration=dict(spec.default_configuration) if spec else None,
            )
        )
    return ProjectRulesResponse(project_id=project_id, rules=rules)


def _get_effective_rules(db, project_id: str) -> list[dict]:
    stored = runtime_db.list_project_rules(db, project_id)
    stored_by_key = {row["rule_key"]: row for row in stored}
    effective = []
    for key, spec in _engine.RULE_REGISTRY.items():
        if key in stored_by_key:
            row = stored_by_key[key]
            effective.append(
                {
                    "rule_key": key,
                    "enabled": bool(row.get("enabled")),
                    "configuration": row.get("configuration") or {},
                }
            )
        else:
            effective.append(
                {
                    "rule_key": key,
                    "enabled": spec.default_enabled,
                    "configuration": dict(spec.default_configuration),
                }
            )
    return effective


# ── Project rules endpoints ──────────────────────────────────────────────────

@project_router.get(
    "/{project_id}/rules",
    response_model=ProjectRulesResponse,
)
def get_project_rules(project_id: str, request: Request) -> ProjectRulesResponse:
    logger.info("api: GET /projects/%s/rules", project_id)
    db = _db_path(request)
    effective = _get_effective_rules(db, project_id)
    return _effective_rules_to_response(project_id, effective)


@project_router.put(
    "/{project_id}/rules",
    response_model=ProjectRulesResponse,
)
def put_project_rules(
    project_id: str,
    payload: ProjectRulesUpdate,
    request: Request,
) -> ProjectRulesResponse:
    logger.info("api: PUT /projects/%s/rules", project_id)
    db = _db_path(request)

    if payload.action == "reset_defaults" or payload.rules is None:
        new_rules = _engine.get_registry_default_rules()
    else:
        new_rules = []
        seen = set()
        for item in payload.rules:
            if item.rule_key in seen:
                raise HTTPException(
                    status_code=422,
                    detail=f"duplicate rule_key '{item.rule_key}'",
                )
            seen.add(item.rule_key)
            _validate_rule_input(item.rule_key, item.configuration)
            new_rules.append(
                {
                    "rule_key": item.rule_key,
                    "enabled": bool(item.enabled),
                    "configuration": item.configuration or {},
                }
            )

    runtime_db.replace_project_rules(db, project_id, new_rules)

    effective = _get_effective_rules(db, project_id)
    return _effective_rules_to_response(project_id, effective)


# ── Ticket rule evaluation endpoints ─────────────────────────────────────────

def _row_to_eval(row: dict) -> TicketRuleEvaluation:
    return TicketRuleEvaluation(
        ticket_id=row["ticket_id"],
        project_id=row["project_id"],
        eligibility_status=row["eligibility_status"],
        passed_rules=[
            RuleEvaluationEntry(**entry) for entry in row.get("passed_rules_json") or []
        ],
        failed_rules=[
            RuleEvaluationEntry(**entry) for entry in row.get("failed_rules_json") or []
        ],
        warnings=[
            RuleWarningEntry(**entry) for entry in row.get("warnings_json") or []
        ],
        evaluated_at=row.get("evaluated_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@ticket_router.get(
    "/{ticket_id}/rule-evaluation",
    response_model=TicketRuleEvaluation,
)
def get_ticket_rule_evaluation(ticket_id: str, request: Request) -> TicketRuleEvaluation:
    logger.info("api: GET /tickets/%s/rule-evaluation", ticket_id)
    _require_ticket(request, ticket_id)
    db = _db_path(request)
    row = runtime_db.get_ticket_rule_evaluation(db, ticket_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"no rule evaluation found for ticket {ticket_id}",
        )
    return _row_to_eval(row)


def _background_evaluate(db, project_id: str, ticket_id: str) -> None:
    try:
        _engine.evaluate_ticket(db, project_id, ticket_id)
    except Exception:
        logger.exception("rule evaluation background error for %s", ticket_id)


@ticket_router.post(
    "/{ticket_id}/evaluate-rules",
    response_model=TicketRuleEvaluationQueued,
    status_code=202,
)
def evaluate_ticket_rules(
    ticket_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    project_id: str | None = None,
) -> TicketRuleEvaluationQueued:
    logger.info("api: POST /tickets/%s/evaluate-rules", ticket_id)
    _require_ticket(request, ticket_id)
    db = _db_path(request)

    # Resolve project_id: prefer the explicit one from the project-scoped route,
    # otherwise fall back to the previously-stored evaluation (if any), else the
    # runtime project_id (Postgres handle) or "default".
    pid = project_id
    if pid is None:
        existing = runtime_db.get_ticket_rule_evaluation(db, ticket_id)
        if existing:
            pid = existing.get("project_id")
    if pid is None:
        pid = getattr(db, "project_id", None) or "default"

    background_tasks.add_task(_background_evaluate, db, pid, ticket_id)
    return TicketRuleEvaluationQueued(status="scheduled", ticket_id=ticket_id)


# ── Project-scoped ticket mounts ─────────────────────────────────────────────

@project_ticket_router.get(
    "/{project_id}/tickets/{ticket_id}/rule-evaluation",
    response_model=TicketRuleEvaluation,
)
def get_ticket_rule_evaluation_project(
    project_id: str, ticket_id: str, request: Request
) -> TicketRuleEvaluation:
    return get_ticket_rule_evaluation(ticket_id, request)


@project_ticket_router.post(
    "/{project_id}/tickets/{ticket_id}/evaluate-rules",
    response_model=TicketRuleEvaluationQueued,
    status_code=202,
)
def evaluate_ticket_rules_project(
    project_id: str,
    ticket_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
) -> TicketRuleEvaluationQueued:
    return evaluate_ticket_rules(
        ticket_id, request, background_tasks, project_id=project_id
    )
