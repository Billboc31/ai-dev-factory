"""Detect the primary technology stack of a project from file presence heuristics."""

from __future__ import annotations

from pathlib import Path


def detect_stack(project_root: Path) -> str:
    """Return the primary stack identifier for *project_root*.

    Checks for well-known manifest files in order of priority and returns the
    first match.  Returns ``"unknown"`` when nothing recognisable is found.
    """
    checks = [
        ("python", ["pyproject.toml", "requirements.txt", "setup.py", "setup.cfg"]),
        ("node", ["package.json"]),
        ("go", ["go.mod"]),
        ("rust", ["Cargo.toml"]),
    ]
    for stack, markers in checks:
        if any((project_root / m).exists() for m in markers):
            return stack
    return "unknown"
