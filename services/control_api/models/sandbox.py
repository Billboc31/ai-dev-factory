from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class SandboxStatus(str, Enum):
    creating = "creating"
    running = "running"
    stopped = "stopped"
    error = "error"
    destroyed = "destroyed"


class LifecyclePhase(str, Enum):
    """Fine-grained deploy lifecycle (environments / operational runtime)."""

    provisioning = "provisioning"
    bootstrapping = "bootstrapping"
    building = "building"
    starting = "starting"
    healthchecking = "healthchecking"
    validating = "validating"
    running = "running"
    failed = "failed"


class EnvironmentType(str, Enum):
    main = "main"
    develop = "develop"
    integration = "integration"
    preview = "preview"
    sandbox = "sandbox"
    feature = "feature"
    custom = "custom"


class RefType(str, Enum):
    branch = "branch"
    tag = "tag"
    commit = "commit"
    pr_ref = "pr_ref"


class EnvironmentMode(str, Enum):
    persistent = "persistent"
    deploy_and_test = "deploy_and_test"


class SandboxState(BaseModel):
    id: str
    ticket_id: str
    project_root: str
    compose_project: str
    ports: dict[str, int]
    env_file: str = ""  # informational; runtime paths are reconstructed dynamically
    status: SandboxStatus
    created_at: str
    slot: int
    supervisor_port: int = 0
    sandbox_runtime_root: str = ""
    supervisor_pid: int | None = None
    worktree_path: str | None = None
    source_path: str | None = None
    job_type: str | None = None
    completed_at: str | None = None
    urls: dict[str, str] = {}
    env_name: str | None = None
    env_type: EnvironmentType | None = None
    ref: str | None = None
    ref_type: RefType | None = None
    deployment_mode: EnvironmentMode | None = None
    web_host: str | None = None
    api_host: str | None = None
    deployed_at: str | None = None
    stopped_at: str | None = None
    requested_ref: str | None = None
    resolved_ref: str | None = None
    commit_sha: str | None = None
    # When set, runtime files (.env, state.json, runtime/) live here instead of
    # {sandboxes_dir}/{id}/. Path is stored exactly as resolved on the host.
    sandbox_dir: str | None = None
    lifecycle_phase: LifecyclePhase | None = None
    last_step: str | None = None
    lifecycle_error: str | None = None
    healthcheck_status: str | None = None
    smoke_status: str | None = None
    lifecycle_steps: list[dict] = []
