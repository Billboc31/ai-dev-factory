"""Tests for atomic Traefik route file lifecycle."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.proxy_manager import ProxyManager
from services.control_api.services.proxy_route_files import (
    atomic_write_route_file,
    route_file_path,
    safe_remove_route_file,
    validate_route_file,
)


def test_atomic_write_creates_final_file_only(tmp_path):
    routes = tmp_path / "routes"
    final = route_file_path(routes, "env123")
    atomic_write_route_file(final, "http:\n  routers: {}\n  services: {}\n")
    assert final.exists()
    assert list(routes.glob("*.tmp")) == []
    assert validate_route_file(final) is None


def test_atomic_write_replace_is_idempotent(tmp_path):
    routes = tmp_path / "routes"
    final = route_file_path(routes, "env123")
    atomic_write_route_file(final, "http:\n  routers:\n    a: {}\n  services: {}\n")
    atomic_write_route_file(final, "http:\n  routers:\n    b: {}\n  services: {}\n")
    assert "b:" in final.read_text(encoding="utf-8")


def test_validate_route_file_rejects_missing(tmp_path):
    assert "does not exist" in validate_route_file(tmp_path / "nope.yml") or ""


def test_safe_remove_does_not_leave_yml(tmp_path):
    routes = tmp_path / "routes"
    final = route_file_path(routes, "gone")
    atomic_write_route_file(final, "http:\n  routers: {}\n  services: {}\n")
    safe_remove_route_file(final)
    assert not final.exists()


def test_register_does_not_leave_tmp_files(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("stable1", {"api": 8080, "web": 3000})
    assert (mgr.routes_dir / "stable1.yml").exists()
    assert list(mgr.routes_dir.glob(".*.tmp")) == []


def test_unregister_without_remove_keeps_file(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("keep", {"api": 8080, "web": 3000})
    mgr.unregister("keep", remove_route_file=False)
    assert (mgr.routes_dir / "keep.yml").exists()


def test_unregister_with_remove_deletes_file(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("gone", {"api": 8080, "web": 3000})
    mgr.unregister("gone", remove_route_file=True)
    assert not (mgr.routes_dir / "gone.yml").exists()


def test_redeploy_register_replaces_same_filename(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    with patch(
        "services.control_api.services.proxy_network.attach_traefik_to_compose_project",
        return_value=False,
    ):
        mgr.register("env1", {"api": 8080, "web": 3000}, compose_project="sandbox-env1")
        mgr.register("env1", {"api": 8180, "web": 3100}, compose_project="sandbox-env1")
    names = [p.name for p in mgr.routes_dir.glob("env1*")]
    assert names == ["env1.yml"]
    assert "8180" in (mgr.routes_dir / "env1.yml").read_text(encoding="utf-8")
