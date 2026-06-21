#!/usr/bin/env python3
"""Control API — REST facade for ai-dev-factory workflow runtime."""

from __future__ import annotations

import logging
import os
import sys
import time
import traceback
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .routes import approvals, auto_fix, daemon, deployer, environments, health, intelligence, issues, project_map, projects, providers, readiness, runtime_dashboard, sandbox, tickets
from .services.project_registry import ProjectRegistry
from .services.runtime_resolver import resolve_worktrees_dir

_TOOLS_DIR = Path(__file__).resolve().parents[2] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import runtime_db as _runtime_db  # noqa: E402


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("control-api")


def _resolve_default_project_root() -> Path:
    """Pick a project root for ``create_app`` when no explicit value is given.

    Precedence:
      1. ``AI_DEV_FACTORY_PROJECT_ROOT`` env var (Docker / systemd use this).
      2. ``Path.cwd()`` (developer launching uvicorn from the clone).

    Using an env var is the safe escape hatch when the API process runs in
    a container whose CWD (``/app``) is not a git working tree. Operators
    can mount the canonical host clone and point this env var at it.
    """
    explicit = os.environ.get("AI_DEV_FACTORY_PROJECT_ROOT")
    if explicit:
        return Path(explicit).expanduser().resolve()
    return Path.cwd()


def create_app(
    project_root: Path | None = None,
    daemon_exec_cmd: str = "claude --dangerously-skip-permissions",
    worktrees_dir: Path | None = None,
    projects_root: Path | None = None,
) -> FastAPI:
    app = FastAPI(
        title="ai-dev-factory Control API",
        description="REST facade for the ai-dev-factory workflow runtime",
        version="1.0.0",
    )

    _root = project_root or _resolve_default_project_root()
    app.state.project_root = _root
    app.state.daemon_exec_cmd = daemon_exec_cmd
    app.state.worktrees_dir = worktrees_dir or resolve_worktrees_dir(_root)
    app.state.db_path = _runtime_db.get_db_path()
    # Diagnostics: make the active runtime DB backend completely unambiguous at
    # boot (multi-line: backend / host / database / project_id, or path).
    _rdb_backend = os.environ.get("RUNTIME_DB_BACKEND", "sqlite").strip().lower()
    for _line in _runtime_db.describe_backend():
        logger.info("%s", _line)
    # Ensure the runtime store exists (idempotent).
    #  - Postgres mode: fail fast. We validate psycopg + reachability + schema
    #    before reporting healthy and NEVER silently fall back to SQLite (that
    #    would create an invisible API/Postgres + daemon/SQLite split-brain).
    #  - SQLite mode: best-effort. A missing/unreachable local file must not
    #    block boot — the board degrades gracefully to filesystem state.
    if app.state.db_path is not None:
        if _rdb_backend == "postgres":
            _runtime_db.verify_backend_available()
            _runtime_db.check_and_recover_db(app.state.db_path)
            _runtime_db.init_runtime_db(app.state.db_path)
        else:
            try:
                _runtime_db.check_and_recover_db(app.state.db_path)
                _runtime_db.init_runtime_db(app.state.db_path)
            except Exception:
                logger.exception("runtime_db: init/recover failed at startup — continuing")

    _runtime_root_env = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    _runtime_root: Path | None = Path(_runtime_root_env).expanduser().resolve() if _runtime_root_env else None
    app.state.runtime_root = _runtime_root

    # RUNTIME_BASE_ROOT is the explicit parent for multi-project runtimes
    # ({base}/{project_id}). It is the ONLY source for a multi-project base.
    # We never derive it from AI_DEV_FACTORY_RUNTIME_ROOT.parent because that
    # breaks valid single-project setups such as AI_DEV_FACTORY_RUNTIME_ROOT=/runtime
    # (its parent is '/'). When RUNTIME_BASE_ROOT is absent the API starts
    # normally with runtime_base_root=None; multi-project operations that
    # actually need a base raise a clear error at import/bootstrap time.
    _runtime_base_root_env = os.environ.get("RUNTIME_BASE_ROOT")
    _runtime_base_root: Path | None
    if _runtime_base_root_env:
        _runtime_base_root = Path(_runtime_base_root_env).expanduser().resolve()
        if _runtime_base_root == Path("/"):
            raise RuntimeError(
                "RUNTIME_BASE_ROOT resolves to filesystem root '/' — check environment configuration"
            )
    else:
        _runtime_base_root = None
    app.state.runtime_base_root = _runtime_base_root

    _pr = projects_root or (
        Path(os.environ["AI_DEV_FACTORY_PROJECTS_ROOT"]).expanduser().resolve()
        if os.environ.get("AI_DEV_FACTORY_PROJECTS_ROOT")
        else None
    )
    # Prefer explicit parameters, then workspace file (runtime-configured mode), then single-root.
    # Only use load_from_workspace_file when no explicit project_root was provided — that is the
    # "Docker / systemd with AI_DEV_FACTORY_RUNTIME_ROOT" deployment mode.
    if _pr is not None:
        app.state.project_registry = ProjectRegistry(projects_root=_pr)
    elif project_root is None and _runtime_root is not None:
        app.state.project_registry = ProjectRegistry.load_from_workspace_file(_runtime_root)
    else:
        app.state.project_registry = ProjectRegistry.from_single_root(_root)

    # Always ensure the AI Dev Factory repo itself appears as a fully bootstrapped project.
    # resolve_git_root handles worktrees (.git file) and normal clones (.git dir).
    from .services.git_root import resolve_git_root
    from .services.project_bootstrap import auto_bootstrap
    from .services.project_id import normalize_project_id

    _git_root = resolve_git_root(_root)
    if (_git_root / ".git").exists():
        _self_id = normalize_project_id(_git_root.name)
        # When no multi-project base is configured, the current project keeps
        # AI_DEV_FACTORY_RUNTIME_ROOT as its own runtime root directly.
        auto_bootstrap(
            _git_root,
            _self_id,
            _runtime_base_root,
            app.state.project_registry,
            self_runtime_root=_runtime_root,
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("unhandled exception: %s\n%s", exc, traceback.format_exc())
        return JSONResponse(status_code=500, content={"detail": str(exc) or "internal server error"})

    @app.middleware("http")
    async def _log_requests(request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000
        logger.info(
            "api: %s %s → %d (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response

    app.include_router(health.router)
    app.include_router(daemon.router)
    app.include_router(daemon.project_router)
    app.include_router(tickets.router)
    app.include_router(tickets.project_router)
    app.include_router(issues.router)
    app.include_router(providers.router)
    app.include_router(project_map.router)
    app.include_router(project_map.project_router)
    app.include_router(deployer.project_router)
    # T133/T136: /sandboxes — SandboxManager (ticket-worker isolation).
    app.include_router(sandbox.router)
    # T134: /projects/{id}/sandbox/* — one-shot deploy-validation pipeline.
    app.include_router(sandbox.project_router)
    # T137: /sandbox-runs — historical validation run listing and cleanup.
    app.include_router(sandbox.runs_router)
    # T138: /projects/{id}/auto-fix/* — read-only AI fix proposals.
    app.include_router(auto_fix.router)
    # T139: /runtime-dashboard/* — sandbox runs, proposal runs, health, log tailing.
    app.include_router(runtime_dashboard.router)
    # T158: /environments — named environments with configurable Traefik hosts.
    app.include_router(environments.router)
    # T174: /projects/{id}/branches — branch listing for environment creation autocomplete.
    app.include_router(projects.router)
    # T197: /tickets/{id}/intelligence — advisory ticket intelligence analysis.
    app.include_router(intelligence.router)
    app.include_router(intelligence.project_router)
    # T198: /tickets/{id}/readiness — advisory execution eligibility evaluation.
    app.include_router(readiness.router)
    app.include_router(readiness.project_router)
    # T199: /tickets/{id}/approvals — human execution approval workflow.
    app.include_router(approvals.router)
    app.include_router(approvals.project_router)

    return app


app = create_app()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ai-dev-factory Control API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--exec-cmd", default="claude --dangerously-skip-permissions")
    parser.add_argument("--worktrees-dir", default=None)
    parser.add_argument("--projects-root", default=None)
    args = parser.parse_args()

    root = Path(args.project_root).resolve() if args.project_root else _resolve_default_project_root()
    wt_dir = Path(args.worktrees_dir).resolve() if args.worktrees_dir else None
    pr = Path(args.projects_root).resolve() if args.projects_root else None
    _app = create_app(project_root=root, daemon_exec_cmd=args.exec_cmd, worktrees_dir=wt_dir, projects_root=pr)
    uvicorn.run(_app, host=args.host, port=args.port)
