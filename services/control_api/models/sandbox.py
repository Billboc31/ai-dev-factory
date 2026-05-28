from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class SandboxStatus(str, Enum):
    creating = "creating"
    running = "running"
    stopped = "stopped"
    error = "error"
    destroyed = "destroyed"


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
    env_file: str
    status: SandboxStatus
    created_at: str
    slot: int
    supervisor_port: int = 0
    sandbox_runtime_root: str = ""
    supervisor_pid: int | None = None
    worktree_path: str | None = None
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
