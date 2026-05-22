from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ProposalStatus = Literal["idle", "pending", "ready", "rejected", "error"]


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
