"""Routes for the auto-fix proposal workflow (T138).

Exposes read-only patch previews for failed sandboxes. No file is
modified and no sandbox is rerun automatically — the proposal is a
human-reviewable suggestion surfaced in the dashboard.

Architecture::

    Dashboard → GET/POST /projects/{project_id}/auto-fix/*
      → auto_fix_runner (HTTP client)
        → host supervisor
          → auto_fix_proposer (background thread)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..dependencies import resolve_project
from ..services import auto_fix_runner

logger = logging.getLogger("control-api")

router = APIRouter(prefix="/projects", tags=["auto-fix"])


def _supervisor_url() -> str | None:
    return os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/") or None


class ProposeAutoFixRequest(BaseModel):
    exec_cmd: str = "claude --dangerously-skip-permissions"
    sandbox_id: str
    failing_step: str | None = None


@router.post("/{project_id}/auto-fix/propose")
def propose_auto_fix(
    project_id: str,
    body: ProposeAutoFixRequest,
    project_root: Path = Depends(resolve_project),
) -> dict:
    result = auto_fix_runner.propose_auto_fix(
        project_id=project_id,
        project_root=str(project_root),
        exec_cmd=body.exec_cmd,
        sandbox_id=body.sandbox_id,
        failing_step=body.failing_step,
        supervisor_url=_supervisor_url(),
    )
    if result.get("error") == "no_supervisor_url":
        raise HTTPException(
            status_code=503,
            detail="supervisor not configured — set AI_DEV_FACTORY_SUPERVISOR_URL",
        )
    if result.get("error") == "supervisor_unreachable":
        raise HTTPException(status_code=503, detail="supervisor unreachable")
    return result


@router.get("/{project_id}/auto-fix/proposal/{proposal_id}")
def get_proposal(
    project_id: str,
    proposal_id: str,
    project_root: Path = Depends(resolve_project),  # registry validation only
) -> dict:
    proposal = auto_fix_runner.get_proposal(project_id, proposal_id, _supervisor_url())
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"proposal not found: {proposal_id}")
    return proposal


@router.get("/{project_id}/auto-fix/proposals")
def list_proposals(
    project_id: str,
    project_root: Path = Depends(resolve_project),  # registry validation only
) -> dict:
    proposals = auto_fix_runner.list_proposals(project_id, _supervisor_url())
    return {"proposals": proposals}
