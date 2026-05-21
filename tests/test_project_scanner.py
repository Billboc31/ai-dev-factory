"""Unit tests for the project scanner service."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.project_scanner import scan_project


def test_docker_services_detected(tmp_path):
    (tmp_path / "docker-compose.yml").write_text(
        "services:\n  api:\n    image: python\n  web:\n    image: node\n",
        encoding="utf-8",
    )
    result = scan_project(tmp_path)
    assert "api" in result.docker_services
    assert "web" in result.docker_services


def test_docker_services_yaml_variant(tmp_path):
    (tmp_path / "docker-compose.yaml").write_text(
        "services:\n  worker:\n    image: python\n",
        encoding="utf-8",
    )
    result = scan_project(tmp_path)
    assert "worker" in result.docker_services


def test_no_docker_compose(tmp_path):
    result = scan_project(tmp_path)
    assert result.docker_services == []


def test_python_backend_requirements_txt(tmp_path):
    (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
    result = scan_project(tmp_path)
    assert result.python_backend is True


def test_python_backend_pyproject_toml(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'x'\n", encoding="utf-8")
    result = scan_project(tmp_path)
    assert result.python_backend is True


def test_no_python_backend(tmp_path):
    result = scan_project(tmp_path)
    assert result.python_backend is False


def test_node_frontend_detected(tmp_path):
    (tmp_path / "package.json").write_text('{"name": "app"}\n', encoding="utf-8")
    result = scan_project(tmp_path)
    assert result.node_frontend is True


def test_no_node_frontend(tmp_path):
    result = scan_project(tmp_path)
    assert result.node_frontend is False


def test_tool_detection_present(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "services.control_api.services.project_scanner.shutil.which",
        lambda name: f"/usr/bin/{name}" if name in ("git", "docker") else None,
    )
    result = scan_project(tmp_path)
    assert "git" in result.required_tools
    assert "docker" in result.required_tools
    assert "gh" not in result.required_tools
    assert "claude" not in result.required_tools


def test_tool_detection_none(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "services.control_api.services.project_scanner.shutil.which",
        lambda name: None,
    )
    result = scan_project(tmp_path)
    assert result.required_tools == []


def test_deploy_profile_loaded(tmp_path):
    ai_dir = tmp_path / ".ai-dev-factory"
    ai_dir.mkdir()
    (ai_dir / "deploy.yml").write_text(
        "version: 1\n"
        "project: myproject\n"
        "required_tools:\n  - git\n  - docker\n"
        "components:\n"
        "  - name: api\n    type: docker\n    service: api\n"
        "  - name: daemon\n    type: host\n    command: python main.py\n",
        encoding="utf-8",
    )
    result = scan_project(tmp_path)
    assert result.deploy_profile is not None
    assert result.deploy_profile.project == "myproject"
    assert result.deploy_profile.version == 1
    assert result.deploy_profile.required_tools == ["git", "docker"]
    assert len(result.deploy_profile.components) == 2
    api_comp = next(c for c in result.deploy_profile.components if c.name == "api")
    assert api_comp.type == "docker"
    assert api_comp.service == "api"
    daemon_comp = next(c for c in result.deploy_profile.components if c.name == "daemon")
    assert daemon_comp.type == "host"
    assert daemon_comp.command == "python main.py"


def test_deploy_profile_missing(tmp_path):
    result = scan_project(tmp_path)
    assert result.deploy_profile is None


def test_deploy_profile_malformed_returns_none(tmp_path):
    ai_dir = tmp_path / ".ai-dev-factory"
    ai_dir.mkdir()
    (ai_dir / "deploy.yml").write_text("not: valid: yaml: [[[", encoding="utf-8")
    result = scan_project(tmp_path)
    assert result.deploy_profile is None
