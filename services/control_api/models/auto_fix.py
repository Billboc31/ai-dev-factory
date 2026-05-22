from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ProposalStatus = Literal["idle", "pending", "ready", "rejected", "error"]
SessionStatus = Literal["running", "success", "failed", "error"]
IterationStatus = Literal["running", "success", "failed", "error"]


class PatchProposal(BaseModel):
    relative_path: str
    content: str
    valid: bool = True


class AutoFixProposal(BaseModel):
    proposal_id: str
    project_id: str
    sandbox_id: str | None = None
    failing_step: str | None = None
    status: ProposalStatus = "idle"
    reasoning: str | None = None
    patches: list[PatchProposal] = []
    context_snapshot: dict = {}
    created_at: str
    error: str | None = None


class AutoFixIteration(BaseModel):
    iteration: int
    status: IterationStatus = "running"
    changed_files: list[str] = []
    patches: list[PatchProposal] = []
    reasoning: str | None = None
    log_lines: list[str] = []
    steps: list[dict] = []
    error: str | None = None
    started_at: str
    finished_at: str | None = None


class AutoFixSession(BaseModel):
    session_id: str
    project_id: str
    sandbox_id: str | None = None
    max_retries: int
    current_iteration: int = 0
    status: SessionStatus = "running"
    iterations: list[AutoFixIteration] = []
    failing_step: str | None = None
    created_at: str
    finished_at: str | None = None
    error: str | None = None
