"""Tests for analysis_prompt_builder — pure string construction, no I/O."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

from analysis_prompt_builder import build_analysis_prompt  # noqa: E402

_SCAN = {
    "docker_services": ["api", "web"],
    "python_backend": True,
    "node_frontend": False,
    "required_tools": ["git", "docker"],
}

_TREE = "myproject/\n├── src/\n│   └── main.py\n└── requirements.txt"


def test_prompt_contains_file_tree():
    prompt = build_analysis_prompt("/projects/myproject", _SCAN, _TREE)
    assert _TREE in prompt


def test_prompt_contains_deploy_schema():
    prompt = build_analysis_prompt("/projects/myproject", _SCAN, _TREE)
    assert "deploy.yml" in prompt
    assert '"version"' in prompt
    assert '"components"' in prompt
    assert '"required_tools"' in prompt


def test_prompt_instructs_file_generation():
    prompt = build_analysis_prompt("/projects/myproject", _SCAN, _TREE)
    assert ".ai-dev-factory/deploy.yml" in prompt
    assert ".ai-dev-factory/deployment.md" in prompt
    assert ".ai-dev-factory/runtime-notes.md" in prompt
    assert "BEGIN FILE" in prompt
    assert "END FILE" in prompt


def test_prompt_is_deterministic():
    p1 = build_analysis_prompt("/projects/myproject", _SCAN, _TREE)
    p2 = build_analysis_prompt("/projects/myproject", _SCAN, _TREE)
    assert p1 == p2
