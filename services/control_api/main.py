#!/usr/bin/env python3
"""Control API — REST facade for ai-dev-factory workflow runtime."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from .routes import daemon, health, issues, providers, tickets


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
)
logger = logging.getLogger("control-api")


def create_app(
    project_root: Path | None = None,
    daemon_exec_cmd: str = "claude --dangerously-skip-permissions",
) -> FastAPI:
    app = FastAPI(
        title="ai-dev-factory Control API",
        description="REST facade for the ai-dev-factory workflow runtime",
        version="1.0.0",
    )

    app.state.project_root = project_root or Path.cwd()
    app.state.daemon_exec_cmd = daemon_exec_cmd

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
    app.include_router(tickets.router)
    app.include_router(issues.router)
    app.include_router(providers.router)

    return app


app = create_app()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ai-dev-factory Control API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--project-root", default=None)
    parser.add_argument("--exec-cmd", default="claude --dangerously-skip-permissions")
    args = parser.parse_args()

    root = Path(args.project_root).resolve() if args.project_root else Path.cwd()
    _app = create_app(project_root=root, daemon_exec_cmd=args.exec_cmd)
    uvicorn.run(_app, host=args.host, port=args.port)
