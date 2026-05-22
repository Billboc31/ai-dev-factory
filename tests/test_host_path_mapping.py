"""Unit tests for ``ContainerToHostMapper``.

The mapper supports **two** configurable rules driven by environment
variables sourced from ``deploy/.env``:

  - ``CONTAINER_PROJECT_ROOT`` → ``HOST_PROJECT_ROOT``  (typically ``/app``)
  - ``CONTAINER_RUNTIME_ROOT`` → ``HOST_RUNTIME_ROOT``  (typically ``/runtime``)

Resolution order: longest container prefix wins, identity fallback when no
rule matches. A "no rules configured" mapper logs a warning and returns
every path unchanged so the supervisor never crashes on misconfiguration.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))

from path_mapper import ContainerToHostMapper


@pytest.fixture(autouse=True)
def _clear_mapping_env(monkeypatch):
    """Each test starts with no mapping configured."""
    for var in (
        "CONTAINER_PROJECT_ROOT", "HOST_PROJECT_ROOT",
        "CONTAINER_RUNTIME_ROOT", "HOST_RUNTIME_ROOT",
    ):
        monkeypatch.delenv(var, raising=False)


# ── Project-root mapping (the bug we are fixing) ──────────────────────────────

def test_project_root_mapping_translates_app_to_host_clone(monkeypatch):
    monkeypatch.setenv("CONTAINER_PROJECT_ROOT", "/app")
    monkeypatch.setenv("HOST_PROJECT_ROOT", "/Users/me/runtime/ai-dev-factory/clones/ai-dev-factory")
    mapper = ContainerToHostMapper()
    assert (
        mapper.map("/app")
        == "/Users/me/runtime/ai-dev-factory/clones/ai-dev-factory"
    )


def test_project_root_mapping_translates_subpath(monkeypatch):
    monkeypatch.setenv("CONTAINER_PROJECT_ROOT", "/app")
    monkeypatch.setenv("HOST_PROJECT_ROOT", "/host/project")
    mapper = ContainerToHostMapper()
    assert mapper.map("/app/services/x.py") == "/host/project/services/x.py"


def test_project_root_mapping_trailing_slash_tolerated(monkeypatch):
    """Operators may write ``HOST_PROJECT_ROOT=/host/project/`` — that must
    not produce a double-slashed result."""
    monkeypatch.setenv("CONTAINER_PROJECT_ROOT", "/app/")
    monkeypatch.setenv("HOST_PROJECT_ROOT", "/host/project/")
    mapper = ContainerToHostMapper()
    assert mapper.map("/app/file.txt") == "/host/project/file.txt"


# ── Runtime-root mapping (preserves T135 behavior) ────────────────────────────

def test_runtime_root_mapping_translates_runtime_to_host_runtime(monkeypatch):
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/runtime")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/Users/me/runtime/ai-dev-factory")
    mapper = ContainerToHostMapper()
    assert (
        mapper.map("/runtime/worktrees/T135")
        == "/Users/me/runtime/ai-dev-factory/worktrees/T135"
    )


def test_runtime_root_only_no_project_rule(monkeypatch):
    """T135-style single-rule configuration must keep working."""
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/runtime")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/host/runtime")
    mapper = ContainerToHostMapper()
    assert mapper.map("/runtime/runs/T100") == "/host/runtime/runs/T100"
    # Without a project-root rule, /app cannot be resolved — identity is the
    # safe fallback (with a log message), NOT a crash.
    assert mapper.map("/app") == "/app"


# ── Priority + longest prefix ─────────────────────────────────────────────────

def test_priority_longest_prefix_wins(monkeypatch):
    """If two rules could match, the longest container prefix wins.

    This guards against a future operator-set ``CONTAINER_PROJECT_ROOT=/`` or
    similar mistake from absorbing more specific runtime paths.
    """
    monkeypatch.setenv("CONTAINER_PROJECT_ROOT", "/app")
    monkeypatch.setenv("HOST_PROJECT_ROOT", "/host/project")
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/app/runtime")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/host/runtime")
    mapper = ContainerToHostMapper()
    assert mapper.map("/app/runtime/runs") == "/host/runtime/runs"
    assert mapper.map("/app/services/x.py") == "/host/project/services/x.py"


def test_both_rules_each_handle_their_own_root(monkeypatch):
    monkeypatch.setenv("CONTAINER_PROJECT_ROOT", "/app")
    monkeypatch.setenv("HOST_PROJECT_ROOT", "/host/clone")
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/runtime")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/host/runtime")
    mapper = ContainerToHostMapper()
    assert mapper.map("/app") == "/host/clone"
    assert mapper.map("/app/services") == "/host/clone/services"
    assert mapper.map("/runtime/runs/T1") == "/host/runtime/runs/T1"


# ── Fallback / safety ─────────────────────────────────────────────────────────

def test_unmapped_path_returned_as_identity(monkeypatch):
    monkeypatch.setenv("CONTAINER_PROJECT_ROOT", "/app")
    monkeypatch.setenv("HOST_PROJECT_ROOT", "/host/clone")
    mapper = ContainerToHostMapper()
    assert mapper.map("/Users/me/elsewhere/foo") == "/Users/me/elsewhere/foo"


def test_ambiguous_prefix_does_not_match_substring(monkeypatch):
    """``/app`` must not capture ``/applications``."""
    monkeypatch.setenv("CONTAINER_PROJECT_ROOT", "/app")
    monkeypatch.setenv("HOST_PROJECT_ROOT", "/host/clone")
    mapper = ContainerToHostMapper()
    assert mapper.map("/applications/foo") == "/applications/foo"


def test_no_rules_configured_returns_identity_and_warns(monkeypatch, caplog):
    """Misconfiguration must not crash — but it must warn."""
    with caplog.at_level(logging.WARNING, logger="supervisor.path_mapper"):
        mapper = ContainerToHostMapper()
    assert mapper.map("/app/anything") == "/app/anything"
    assert any(
        "no mapping rules configured" in rec.message
        for rec in caplog.records
    )


def test_empty_string_returned_unchanged(monkeypatch):
    monkeypatch.setenv("CONTAINER_PROJECT_ROOT", "/app")
    monkeypatch.setenv("HOST_PROJECT_ROOT", "/host/clone")
    mapper = ContainerToHostMapper()
    assert mapper.map("") == ""


# ── Strategy logging (operator diagnosability) ────────────────────────────────

def test_mapping_logs_strategy_name(monkeypatch, caplog):
    monkeypatch.setenv("CONTAINER_PROJECT_ROOT", "/app")
    monkeypatch.setenv("HOST_PROJECT_ROOT", "/host/clone")
    monkeypatch.setenv("CONTAINER_RUNTIME_ROOT", "/runtime")
    monkeypatch.setenv("HOST_RUNTIME_ROOT", "/host/runtime")

    with caplog.at_level(logging.INFO, logger="supervisor.path_mapper"):
        mapper = ContainerToHostMapper()
        mapper.map("/app/foo")
        mapper.map("/runtime/foo")
        mapper.map("/unmapped/foo")

    messages = [rec.message for rec in caplog.records]
    assert any("mapped via project-root" in m and "/app/foo" in m for m in messages)
    assert any("mapped via runtime-root" in m and "/runtime/foo" in m for m in messages)
    assert any("no rule matched" in m and "/unmapped/foo" in m for m in messages)
