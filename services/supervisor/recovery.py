"""Recovery module for the AI Dev Factory supervisor.

Implements the recover_ticket capability: diagnose a blocked ticket, propose
an allowlisted set of recovery operations, execute them after confirmation,
and file a deduplicated GitHub issue when a reproducible platform bug is found.
"""

from __future__ import annotations

import hashlib
import json
import logging
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Literal

logger = logging.getLogger("supervisor.recovery")

MAX_RECOVERY_ITERATIONS = 3

# ── Enumerations ──────────────────────────────────────────────────────────────


class BlockerClass(str, Enum):
    MISSING_ARTIFACT = "MISSING_ARTIFACT"
    STALE_READINESS = "STALE_READINESS"
    MISSING_APPROVAL = "MISSING_APPROVAL"
    FAILED_STAGE = "FAILED_STAGE"
    BRANCH_DIVERGENCE = "BRANCH_DIVERGENCE"
    WORKING_TREE_CONFLICT = "WORKING_TREE_CONFLICT"
    TRANSIENT_FAILURE = "TRANSIENT_FAILURE"
    INVALID_CONFIG = "INVALID_CONFIG"
    INCONSISTENT_STATE = "INCONSISTENT_STATE"
    PRODUCT_BUG = "PRODUCT_BUG"
    USER_DECISION_REQUIRED = "USER_DECISION_REQUIRED"


class RecoveryStage(str, Enum):
    DIAGNOSING = "DIAGNOSING"
    PLAN_READY = "PLAN_READY"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    APPLYING_FIX = "APPLYING_FIX"
    RETRYING_STAGE = "RETRYING_STAGE"
    VERIFYING = "VERIFYING"
    RECOVERED = "RECOVERED"
    NEEDS_USER_INPUT = "NEEDS_USER_INPUT"
    BUG_REPORTED = "BUG_REPORTED"
    FAILED = "FAILED"


class ProposalStatus(str, Enum):
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    INVALIDATED = "INVALIDATED"


class ArtifactType(str, Enum):
    PLAN = "PLAN"
    PLAN_REVIEW = "PLAN_REVIEW"
    STATE = "STATE"
    FIX_CONTEXT = "FIX_CONTEXT"
    CONTEXT = "CONTEXT"


class ServiceId(str, Enum):
    DAEMON = "DAEMON"
    RUNNER = "RUNNER"


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class RecoveryOp:
    name: str
    description: str
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    params: dict


@dataclass
class StateFingerprint:
    ticket_id: str
    ticket_state: str
    blocked_stage: str | None
    artifact_hashes: dict[str, str]
    version: str


@dataclass
class RecoveryProposal:
    proposal_id: str
    project_id: str
    ticket_id: str
    blocker_class: BlockerClass
    operations: list[RecoveryOp]
    state_fingerprint: StateFingerprint
    created_at: datetime
    status: ProposalStatus


@dataclass
class RecoverySession:
    session_id: str
    proposal_id: str | None
    ticket_id: str
    stage: RecoveryStage
    iteration_count: int
    operations_log: list[dict] = field(default_factory=list)


@dataclass
class OpResult:
    op_name: str
    success: bool
    detail: str
    mutated: bool


@dataclass
class RecoveryResult:
    session_id: str
    proposal_id: str | None
    ticket_id: str
    stage: RecoveryStage
    root_cause: str
    ops_performed: list[dict]
    new_ticket_state: str | None
    bug_issue_url: str | None
    error: str | None


# ── Pipeline stage names ──────────────────────────────────────────────────────

_PIPELINE_STAGES = frozenset({
    "PLAN",
    "PLAN_REVIEW",
    "PLAN_FIX",
    "IMPLEMENTATION",
    "IMPLEMENTATION_REVIEW",
    "TEST",
    "MEMORY_UPDATE",
    "MEMORY_REVIEW",
    "RISK_CLASSIFICATION",
})

# States that indicate a human approval gate is open.
_PENDING_REVIEW_STATES = frozenset({
    "PLAN_PENDING_REVIEW",
    "IMPLEMENTATION_PENDING_REVIEW",
    "MEMORY_PENDING_REVIEW",
})

# Terminal states — ticket is done and no longer active.
_TERMINAL_TICKET_STATES = frozenset({
    "DONE",
    "MERGED",
    "CLOSED",
    "CANCELLED",
})


# ── Artifact path helpers ─────────────────────────────────────────────────────

def _ticket_run_dir(project_root: Path, ticket_id: str) -> Path:
    return project_root / "runs" / ticket_id


def _artifact_paths_for_ticket(project_root: Path, ticket_id: str) -> dict[str, Path]:
    """Return a mapping of relative path → absolute Path for known artifacts."""
    run_dir = _ticket_run_dir(project_root, ticket_id)
    paths: dict[str, Path] = {}
    for name in ("state.json", "plan.md", "review.json", "workflow-status.md"):
        p = run_dir / name
        paths[name] = p
    reviews_dir = run_dir / "reviews"
    if reviews_dir.exists():
        for p in sorted(reviews_dir.glob("*.md")):
            paths[f"reviews/{p.name}"] = p
    fixes_dir = run_dir / "fixes"
    if fixes_dir.exists():
        for p in sorted(fixes_dir.glob("*.md")):
            paths[f"fixes/{p.name}"] = p
    return paths


def _sha256_file(path: Path) -> str:
    try:
        data = path.read_bytes()
        return hashlib.sha256(data).hexdigest()
    except OSError:
        return ""


# ── Op parameter schema validator ─────────────────────────────────────────────


def _validate_params(params: dict, param_schema: dict) -> None:
    """Raise ValueError if params contains unknown keys or invalid values."""
    for key, value in params.items():
        if key not in param_schema:
            raise ValueError(f"param {key!r} not accepted by op")
        spec = param_schema[key]
        if spec["type"] == "enum" and value not in spec["values"]:
            raise ValueError(
                f"param {key!r}={value!r} is not in the allowed set {spec['values']!r}"
            )


# ── Internal op implementations ───────────────────────────────────────────────


def _op_regenerate_artifact(
    op: RecoveryOp, project_root: Path, project_id: str, ticket_id: str
) -> OpResult:
    artifact_type = op.params.get("artifact_type", "STATE")
    run_dir = _ticket_run_dir(project_root, ticket_id)

    target_map: dict[str, Path] = {
        ArtifactType.PLAN.value: run_dir / "plan.md",
        ArtifactType.PLAN_REVIEW.value: run_dir / "reviews" / "plan-review-recovered.md",
        ArtifactType.STATE.value: run_dir / "state.json",
        ArtifactType.FIX_CONTEXT.value: run_dir / "fixes" / "context-recovered.md",
        ArtifactType.CONTEXT.value: run_dir / "fixes" / "context-recovered.md",
    }
    target = target_map.get(artifact_type)
    if target is None:
        return OpResult(op_name=op.name, success=False, detail=f"unknown artifact_type {artifact_type!r}", mutated=False)

    if target.exists():
        return OpResult(op_name=op.name, success=True, detail=f"{artifact_type} already present at {target.name}", mutated=False)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if artifact_type == ArtifactType.STATE.value:
            target.write_text(
                json.dumps({"ticket_id": ticket_id, "state": "PLAN", "recovered": True}),
                encoding="utf-8",
            )
        else:
            target.write_text(
                f"# Recovered {artifact_type}\n\nRegenerated by recovery agent.\n",
                encoding="utf-8",
            )
        return OpResult(op_name=op.name, success=True, detail=f"regenerated {target.name}", mutated=True)
    except OSError as exc:
        return OpResult(op_name=op.name, success=False, detail=str(exc), mutated=False)


def _op_refresh_readiness(
    op: RecoveryOp, project_root: Path, project_id: str, ticket_id: str
) -> OpResult:
    run_dir = _ticket_run_dir(project_root, ticket_id)
    state_file = run_dir / "state.json"
    try:
        state_data = json.loads(state_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return OpResult(op_name=op.name, success=False, detail=str(exc), mutated=False)

    state_data["readiness_refreshed_at"] = datetime.now(timezone.utc).isoformat()
    try:
        state_file.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
        return OpResult(op_name=op.name, success=True, detail="readiness timestamp refreshed", mutated=True)
    except OSError as exc:
        return OpResult(op_name=op.name, success=False, detail=str(exc), mutated=False)


def _op_retry_stage(
    op: RecoveryOp, project_root: Path, project_id: str, ticket_id: str
) -> OpResult:
    stage_name = op.params.get("stage_name", "auto")
    if stage_name == "auto":
        run_dir = _ticket_run_dir(project_root, ticket_id)
        try:
            state_data = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
            stage_name = state_data.get("state", "PLAN")
        except (OSError, json.JSONDecodeError):
            stage_name = "PLAN"

    # Write a retry marker that the daemon can pick up
    run_dir = _ticket_run_dir(project_root, ticket_id)
    retry_file = run_dir / "retry_stage.json"
    try:
        retry_file.parent.mkdir(parents=True, exist_ok=True)
        retry_file.write_text(
            json.dumps({"stage": stage_name, "requested_at": datetime.now(timezone.utc).isoformat()}),
            encoding="utf-8",
        )
        return OpResult(op_name=op.name, success=True, detail=f"retry marker written for stage {stage_name!r}", mutated=True)
    except OSError as exc:
        return OpResult(op_name=op.name, success=False, detail=str(exc), mutated=False)


def _op_fetch_branch(
    op: RecoveryOp, project_root: Path, project_id: str, ticket_id: str
) -> OpResult:
    run_dir = _ticket_run_dir(project_root, ticket_id)
    branch = None
    try:
        state_data = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        branch = state_data.get("branch")
    except (OSError, json.JSONDecodeError):
        pass

    if not branch:
        return OpResult(op_name=op.name, success=False, detail="no branch configured in state.json", mutated=False)

    try:
        result = subprocess.run(
            ["git", "fetch", "origin", branch],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            return OpResult(op_name=op.name, success=True, detail=f"fetched {branch}", mutated=False)
        return OpResult(op_name=op.name, success=False, detail=result.stderr.strip()[:200], mutated=False)
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return OpResult(op_name=op.name, success=False, detail=str(exc), mutated=False)


def _op_restart_service(
    op: RecoveryOp, project_root: Path, project_id: str, ticket_id: str
) -> OpResult:
    service_id = op.params.get("service_id", "")
    # Signal restart by writing a marker; actual service restart is handled by supervisor
    run_dir = _ticket_run_dir(project_root, ticket_id)
    restart_file = run_dir / f"restart_{service_id.lower()}.json"
    try:
        restart_file.parent.mkdir(parents=True, exist_ok=True)
        restart_file.write_text(
            json.dumps({"service": service_id, "requested_at": datetime.now(timezone.utc).isoformat()}),
            encoding="utf-8",
        )
        return OpResult(op_name=op.name, success=True, detail=f"restart requested for {service_id}", mutated=True)
    except OSError as exc:
        return OpResult(op_name=op.name, success=False, detail=str(exc), mutated=False)


def _op_run_diagnostics(
    op: RecoveryOp, project_root: Path, project_id: str, ticket_id: str
) -> OpResult:
    run_dir = _ticket_run_dir(project_root, ticket_id)
    findings: list[str] = []

    state_file = run_dir / "state.json"
    if state_file.exists():
        try:
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
            findings.append(f"state={state_data.get('state', 'unknown')}")
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(f"state.json unreadable: {exc}")
    else:
        findings.append("state.json missing")

    plan_file = run_dir / "plan.md"
    findings.append(f"plan.md={'present' if plan_file.exists() else 'missing'}")

    log_file = run_dir / "runtime.log"
    if log_file.exists():
        try:
            tail = log_file.read_text(encoding="utf-8", errors="replace")[-2000:]
            error_lines = [l for l in tail.splitlines() if "ERROR" in l or "CRITICAL" in l]
            findings.append(f"log errors: {len(error_lines)}")
        except OSError:
            pass

    return OpResult(
        op_name=op.name,
        success=True,
        detail="; ".join(findings),
        mutated=False,
    )


def _op_create_bug_issue(
    op: RecoveryOp, project_root: Path, project_id: str, ticket_id: str
) -> OpResult:
    # Deduplication and creation are handled by the module-level functions;
    # this op is a no-op placeholder — callers invoke create_bug_issue directly.
    return OpResult(op_name=op.name, success=True, detail="bug issue creation delegated to recovery executor", mutated=False)


# ── Allowlist ─────────────────────────────────────────────────────────────────


@dataclass
class OpSpec:
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    param_schema: dict  # key → {"type": "enum", "values": set}
    internal_fn: Callable[[RecoveryOp, Path, str, str], OpResult]
    preconditions: list[str]
    mutation_description: str
    success_condition: str
    retry_policy: dict  # max_attempts, backoff_seconds


ALLOWLISTED_RECOVERY_OPS: dict[str, OpSpec] = {
    "regenerate_artifact": OpSpec(
        risk_level="LOW",
        param_schema={
            "artifact_type": {"type": "enum", "values": {at.value for at in ArtifactType}},
        },
        internal_fn=_op_regenerate_artifact,
        preconditions=["artifact file is missing or malformed"],
        mutation_description="Writes a derived artifact file using the repository convention",
        success_condition="artifact file exists and is readable",
        retry_policy={"max_attempts": 2, "backoff_seconds": 1},
    ),
    "refresh_readiness": OpSpec(
        risk_level="LOW",
        param_schema={},
        internal_fn=_op_refresh_readiness,
        preconditions=["ticket has a valid state.json"],
        mutation_description="Writes a readiness_refreshed_at timestamp to state.json",
        success_condition="state.json contains updated readiness timestamp",
        retry_policy={"max_attempts": 2, "backoff_seconds": 1},
    ),
    "retry_stage": OpSpec(
        risk_level="MEDIUM",
        param_schema={
            "stage_name": {"type": "enum", "values": _PIPELINE_STAGES | {"auto"}},
        },
        internal_fn=_op_retry_stage,
        preconditions=["pipeline stage is known and failed"],
        mutation_description="Writes a retry_stage.json marker for the daemon",
        success_condition="retry_stage.json written; daemon picks it up",
        retry_policy={"max_attempts": 1, "backoff_seconds": 0},
    ),
    "fetch_branch": OpSpec(
        risk_level="MEDIUM",
        param_schema={},
        internal_fn=_op_fetch_branch,
        preconditions=["branch is configured in state.json"],
        mutation_description="Runs git fetch for the ticket branch (read from project config)",
        success_condition="git fetch exits 0",
        retry_policy={"max_attempts": 2, "backoff_seconds": 5},
    ),
    "restart_service": OpSpec(
        risk_level="HIGH",
        param_schema={
            "service_id": {"type": "enum", "values": {si.value for si in ServiceId}},
        },
        internal_fn=_op_restart_service,
        preconditions=["service_id is DAEMON or RUNNER"],
        mutation_description="Writes a restart marker for the named approved service",
        success_condition="restart marker written",
        retry_policy={"max_attempts": 1, "backoff_seconds": 0},
    ),
    "run_diagnostics": OpSpec(
        risk_level="LOW",
        param_schema={},
        internal_fn=_op_run_diagnostics,
        preconditions=[],
        mutation_description="Read-only: collects state, log, and artifact information",
        success_condition="diagnostic report produced",
        retry_policy={"max_attempts": 1, "backoff_seconds": 0},
    ),
    "create_bug_issue": OpSpec(
        risk_level="MEDIUM",
        param_schema={},
        internal_fn=_op_create_bug_issue,
        preconditions=["reproducible product bug identified"],
        mutation_description="Delegates to executor to create a sanitized GitHub issue",
        success_condition="issue URL recorded in recovery report",
        retry_policy={"max_attempts": 1, "backoff_seconds": 0},
    ),
}


# ── Core functions ────────────────────────────────────────────────────────────


def compute_state_fingerprint(
    ticket_id: str, project_root: Path, ops: list[RecoveryOp]
) -> StateFingerprint:
    """Read state.json and relevant artifact files; return a deterministic fingerprint."""
    run_dir = _ticket_run_dir(project_root, ticket_id)
    state_file = run_dir / "state.json"

    ticket_state = ""
    blocked_stage = None
    try:
        state_data = json.loads(state_file.read_text(encoding="utf-8"))
        ticket_state = state_data.get("state", "")
        blocked_stage = state_data.get("blocked_stage") or state_data.get("stage")
    except (OSError, json.JSONDecodeError):
        pass

    artifact_paths = _artifact_paths_for_ticket(project_root, ticket_id)
    artifact_hashes: dict[str, str] = {}
    for rel, path in artifact_paths.items():
        if path.exists():
            artifact_hashes[rel] = _sha256_file(path)

    # Deterministic version digest
    digest_input = json.dumps(
        {
            "ticket_id": ticket_id,
            "ticket_state": ticket_state,
            "blocked_stage": blocked_stage,
            "artifact_hashes": artifact_hashes,
        },
        sort_keys=True,
    ).encode()
    version = hashlib.sha256(digest_input).hexdigest()

    return StateFingerprint(
        ticket_id=ticket_id,
        ticket_state=ticket_state,
        blocked_stage=blocked_stage,
        artifact_hashes=artifact_hashes,
        version=version,
    )


def classify_blocker(
    state_data: dict, artifacts: dict, logs: str
) -> BlockerClass:
    """Pure function: classify the blocker from structured state, artifacts, and log text."""
    state = state_data.get("state", "")
    log_lower = logs.lower()

    # Missing approval gate
    if state in _PENDING_REVIEW_STATES:
        return BlockerClass.MISSING_APPROVAL

    # User decision required
    if state == "NEEDS_USER_INPUT" or state_data.get("needs_user_input"):
        return BlockerClass.USER_DECISION_REQUIRED

    # Invalid config — missing required state fields
    if not state or state_data.get("invalid_config"):
        return BlockerClass.INVALID_CONFIG

    # Check for product bugs (framework tracebacks / internal errors before transient)
    if (
        "traceback (most recent call last)" in log_lower
        or "attributeerror" in log_lower
        or "internal error" in log_lower
        or state_data.get("product_bug")
    ):
        return BlockerClass.PRODUCT_BUG

    # Working tree conflict
    if (
        "conflict" in log_lower
        or "<<<<<<" in logs
        or state_data.get("working_tree_conflict")
    ):
        return BlockerClass.WORKING_TREE_CONFLICT

    # Branch divergence
    if (
        "diverged" in log_lower
        or "non-fast-forward" in log_lower
        or "rejected" in log_lower
        or state_data.get("branch_divergence")
    ):
        return BlockerClass.BRANCH_DIVERGENCE

    # Transient failure (network/process)
    if (
        "timeout" in log_lower
        or "connection refused" in log_lower
        or "network error" in log_lower
        or "connection reset" in log_lower
        or state_data.get("transient_failure")
    ):
        return BlockerClass.TRANSIENT_FAILURE

    # Stale readiness (explicit marker from state)
    if state_data.get("stale_readiness"):
        return BlockerClass.STALE_READINESS

    # Inconsistent state (contradictory values)
    if state_data.get("inconsistent_state"):
        return BlockerClass.INCONSISTENT_STATE

    # Failed stage — error in logs without a more specific classification
    if (
        "error" in log_lower
        or "failed" in log_lower
        or state_data.get("failed_stage")
    ):
        return BlockerClass.FAILED_STAGE

    # Missing artifact — expected file absent for the current state
    expected_artifacts = {
        "PLAN_APPROVED": "plan.md",
        "IMPLEMENTATION": "plan.md",
        "TEST": "plan.md",
    }
    expected = expected_artifacts.get(state)
    if expected and not artifacts.get(expected):
        return BlockerClass.MISSING_ARTIFACT

    # Default for stale readiness when no other signal is present
    return BlockerClass.STALE_READINESS


def build_recovery_plan(
    blocker: BlockerClass, state_data: dict
) -> list[RecoveryOp]:
    """Deterministic mapping from blocker class to an ordered list of allowlisted ops."""
    current_state = state_data.get("state", "")

    plans: dict[BlockerClass, list[dict]] = {
        BlockerClass.MISSING_ARTIFACT: [
            {
                "name": "run_diagnostics",
                "description": "Collect diagnostics to identify missing artifact",
                "risk_level": "LOW",
                "params": {},
            },
            {
                "name": "regenerate_artifact",
                "description": "Regenerate the missing derived artifact",
                "risk_level": "LOW",
                "params": {"artifact_type": "STATE"},
            },
            {
                "name": "refresh_readiness",
                "description": "Re-evaluate readiness rules after artifact restore",
                "risk_level": "LOW",
                "params": {},
            },
        ],
        BlockerClass.STALE_READINESS: [
            {
                "name": "refresh_readiness",
                "description": "Re-evaluate stale readiness rules",
                "risk_level": "LOW",
                "params": {},
            },
        ],
        BlockerClass.MISSING_APPROVAL: [],  # No mutating ops — terminates with NEEDS_USER_INPUT
        BlockerClass.FAILED_STAGE: [
            {
                "name": "run_diagnostics",
                "description": "Collect diagnostics for the failed stage",
                "risk_level": "LOW",
                "params": {},
            },
            {
                "name": "retry_stage",
                "description": f"Retry the failed pipeline stage ({current_state or 'auto'})",
                "risk_level": "MEDIUM",
                "params": {"stage_name": current_state if current_state in _PIPELINE_STAGES else "auto"},
            },
        ],
        BlockerClass.BRANCH_DIVERGENCE: [
            {
                "name": "fetch_branch",
                "description": "Fetch the ticket branch from origin",
                "risk_level": "MEDIUM",
                "params": {},
            },
        ],
        BlockerClass.WORKING_TREE_CONFLICT: [],  # Requires user intervention
        BlockerClass.TRANSIENT_FAILURE: [
            {
                "name": "run_diagnostics",
                "description": "Collect diagnostics after transient failure",
                "risk_level": "LOW",
                "params": {},
            },
            {
                "name": "retry_stage",
                "description": "Retry the stage after transient failure",
                "risk_level": "MEDIUM",
                "params": {"stage_name": "auto"},
            },
        ],
        BlockerClass.INVALID_CONFIG: [
            {
                "name": "run_diagnostics",
                "description": "Diagnose the invalid configuration",
                "risk_level": "LOW",
                "params": {},
            },
        ],
        BlockerClass.INCONSISTENT_STATE: [
            {
                "name": "run_diagnostics",
                "description": "Diagnose the inconsistent state",
                "risk_level": "LOW",
                "params": {},
            },
            {
                "name": "refresh_readiness",
                "description": "Refresh readiness to resolve inconsistency",
                "risk_level": "LOW",
                "params": {},
            },
        ],
        BlockerClass.PRODUCT_BUG: [
            {
                "name": "run_diagnostics",
                "description": "Collect evidence of the product bug",
                "risk_level": "LOW",
                "params": {},
            },
            {
                "name": "create_bug_issue",
                "description": "File a deduplicated GitHub issue for the product bug",
                "risk_level": "MEDIUM",
                "params": {},
            },
        ],
        BlockerClass.USER_DECISION_REQUIRED: [],  # Requires user input
    }

    raw_ops = plans.get(blocker, [])
    result: list[RecoveryOp] = []
    for op_dict in raw_ops:
        name = op_dict["name"]
        if name not in ALLOWLISTED_RECOVERY_OPS:
            raise ValueError(f"op {name!r} is not in ALLOWLISTED_RECOVERY_OPS")
        spec = ALLOWLISTED_RECOVERY_OPS[name]
        params = op_dict.get("params", {})
        _validate_params(params, spec.param_schema)
        result.append(
            RecoveryOp(
                name=name,
                description=op_dict["description"],
                risk_level=op_dict["risk_level"],
                params=params,
            )
        )
    return result


def compute_bug_signature(
    project_id: str,
    blocker_class: BlockerClass,
    failed_stage: str | None,
    error_code: str | None,
    affected_component: str | None,
) -> str:
    """Deterministic deduplication key from structured fields only."""
    parts = {
        "project_id": project_id,
        "blocker_class": blocker_class.value,
        "failed_stage": failed_stage or "",
        "error_code": error_code or "",
        "affected_component": affected_component or "",
    }
    digest_input = json.dumps(parts, sort_keys=True).encode()
    return hashlib.sha256(digest_input).hexdigest()[:16]


def search_existing_bug_issues(repo: str, signature: str) -> str | None:
    """Search open GitHub issues for signature string; return URL or None."""
    try:
        result = subprocess.run(
            [
                "gh", "issue", "list",
                "--repo", repo,
                "--state", "open",
                "--search", f"recovery-bug-sig:{signature}",
                "--json", "url",
                "--limit", "1",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout.strip() or "[]")
        if data:
            return data[0].get("url")
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
        pass
    return None


def create_bug_issue(
    repo: str,
    session: RecoverySession,
    proposal: RecoveryProposal,
    error_summary: str,
) -> str:
    """Create a sanitized GitHub bug issue; return the issue URL."""
    sig = compute_bug_signature(
        project_id=proposal.project_id,
        blocker_class=proposal.blocker_class,
        failed_stage=proposal.state_fingerprint.blocked_stage,
        error_code=None,
        affected_component=None,
    )
    title = (
        f"[Bug] Recovery failure: {proposal.blocker_class.value} "
        f"in {proposal.project_id}/{proposal.ticket_id}"
    )
    body = (
        f"**recovery-bug-sig:{sig}**\n\n"
        f"## Affected pipeline stage\n\n{proposal.state_fingerprint.blocked_stage or 'unknown'}\n\n"
        f"## Ticket / Project\n\n"
        f"- Project: `{proposal.project_id}`\n"
        f"- Ticket: `{proposal.ticket_id}`\n"
        f"- Session: `{session.session_id}`\n\n"
        f"## Expected behavior\n\nThe pipeline stage should complete without error.\n\n"
        f"## Actual behavior\n\n{error_summary[:1000]}\n\n"
        f"## Blocker class\n\n`{proposal.blocker_class.value}`\n\n"
        f"## Operations attempted\n\n"
        + "\n".join(f"- `{op['op_name']}`: {op.get('detail', '')}" for op in session.operations_log)
        + "\n\n## Reproduction steps\n\n"
        "1. Run the recovery action for the above ticket.\n"
        "2. Observe the failure.\n"
    )

    result = subprocess.run(
        ["gh", "issue", "create", "--repo", repo, "--title", title, "--body", body],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh issue create failed: {result.stderr.strip()[:200]}")
    return result.stdout.strip()


def apply_recovery_op(
    op: RecoveryOp,
    project_root: Path,
    project_id: str,
    ticket_id: str,
) -> OpResult:
    """Execute a single recovery op after double-checking the allowlist."""
    if op.name not in ALLOWLISTED_RECOVERY_OPS:
        raise ValueError(f"op {op.name!r} is not in ALLOWLISTED_RECOVERY_OPS")
    spec = ALLOWLISTED_RECOVERY_OPS[op.name]
    _validate_params(op.params, spec.param_schema)
    try:
        result = spec.internal_fn(op, project_root, project_id, ticket_id)
        logger.info(
            "recovery: op=%s ticket=%s success=%s detail=%r",
            op.name, ticket_id, result.success, result.detail,
        )
        return result
    except Exception as exc:
        logger.error("recovery: op=%s ticket=%s raised: %s", op.name, ticket_id, exc, exc_info=True)
        return OpResult(op_name=op.name, success=False, detail=str(exc), mutated=False)


def verify_ticket_progress(
    ticket_id: str, project_root: Path, expected_next_state: str
) -> tuple[bool, str]:
    """Read state.json and return (True, new_state) if state advanced, else (False, current_state)."""
    run_dir = _ticket_run_dir(project_root, ticket_id)
    state_file = run_dir / "state.json"
    try:
        state_data = json.loads(state_file.read_text(encoding="utf-8"))
        current = state_data.get("state", "")
    except (OSError, json.JSONDecodeError) as exc:
        return False, str(exc)

    if current == expected_next_state:
        return True, current
    if current in _TERMINAL_TICKET_STATES:
        return True, current
    return False, current
