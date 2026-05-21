from __future__ import annotations

import logging
import shutil
from pathlib import Path

import yaml

from ..models.schemas import DeployComponent, DeployProfile, ScanResult

logger = logging.getLogger("control-api")

_TRACKED_TOOLS = ["gh", "git", "docker", "claude"]


def scan_project(project_root: Path) -> ScanResult:
    docker_services = _detect_docker_services(project_root)
    python_backend = _detect_python_backend(project_root)
    node_frontend = _detect_node_frontend(project_root)
    required_tools = _detect_tools()
    deploy_profile = _load_deploy_profile(project_root)

    return ScanResult(
        docker_services=docker_services,
        python_backend=python_backend,
        node_frontend=node_frontend,
        required_tools=required_tools,
        deploy_profile=deploy_profile,
    )


def _detect_docker_services(root: Path) -> list[str]:
    for name in ("docker-compose.yml", "docker-compose.yaml"):
        compose_file = root / name
        if compose_file.exists():
            try:
                data = yaml.safe_load(compose_file.read_text(encoding="utf-8"))
                services = data.get("services") if isinstance(data, dict) else None
                if isinstance(services, dict):
                    return list(services.keys())
            except Exception:
                logger.warning("scanner: failed to parse %s", compose_file)
            break
    return []


def _detect_python_backend(root: Path) -> bool:
    return (root / "requirements.txt").exists() or (root / "pyproject.toml").exists()


def _detect_node_frontend(root: Path) -> bool:
    return (root / "package.json").exists()


def _detect_tools() -> list[str]:
    return [tool for tool in _TRACKED_TOOLS if shutil.which(tool) is not None]


def _load_deploy_profile(root: Path) -> DeployProfile | None:
    profile_path = root / ".ai-dev-factory" / "deploy.yml"
    if not profile_path.exists():
        return None
    try:
        data = yaml.safe_load(profile_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        components = [
            DeployComponent(
                name=c["name"],
                type=c["type"],
                service=c.get("service"),
                command=c.get("command"),
            )
            for c in (data.get("components") or [])
        ]
        return DeployProfile(
            version=data["version"],
            project=data["project"],
            required_tools=data.get("required_tools") or [],
            components=components,
        )
    except Exception:
        logger.warning("scanner: failed to parse deploy.yml at %s", profile_path)
        return None
