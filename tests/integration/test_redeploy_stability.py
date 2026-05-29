"""Integration: redeploying the same sandbox leaves a valid, stable route.

Verifies that repeated register() calls produce a single well-formed route file
with the same alias-based backend URL — no orphaned files and no watcher races.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.control_api.services.proxy_manager import ProxyManager


def test_redeploy_leaves_single_route_file(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("envredeploy")
    mgr.register("envredeploy")

    yml_files = [f for f in mgr.routes_dir.glob("envredeploy*") if not f.name.startswith(".")]
    assert yml_files == [mgr.routes_dir / "envredeploy.yml"]


def test_redeploy_route_contains_alias_backend(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("envredeploy")
    mgr.register("envredeploy")

    content = (mgr.routes_dir / "envredeploy.yml").read_text()
    assert "sandbox-envredeploy-api:8080" in content
    assert "sandbox-envredeploy-web:80" in content


def test_redeploy_returns_same_pretty_urls(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    urls1 = mgr.register("envredeploy")
    urls2 = mgr.register("envredeploy")

    assert urls1 == urls2


def test_redeploy_no_tmp_files_left(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("envredeploy")
    mgr.register("envredeploy")

    assert list(mgr.routes_dir.glob(".*.tmp")) == []
