"""Integration: destroying one sandbox does not affect concurrent sandboxes.

Verifies that unregister(remove_route_file=True) removes only the target route
and leaves all other routes and the _dashboard infra route untouched.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.control_api.services.proxy_manager import ProxyManager


def test_destroy_one_sandbox_leaves_other_intact(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("sandboxA")
    mgr.register("sandboxB")

    mgr.unregister("sandboxA", remove_route_file=True)

    assert not (mgr.routes_dir / "sandboxA.yml").exists()
    assert (mgr.routes_dir / "sandboxB.yml").exists()


def test_destroy_does_not_remove_infra_dashboard(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("sandboxA")

    mgr.unregister("sandboxA", remove_route_file=True)

    assert (mgr.routes_dir / "_dashboard.yml").exists()


def test_surviving_sandbox_route_still_uses_alias_backend(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("sandboxA")
    mgr.register("sandboxB")

    mgr.unregister("sandboxA", remove_route_file=True)

    content = (mgr.routes_dir / "sandboxB.yml").read_text()
    assert "sandbox-sandboxb-api:8080" in content
    assert "sandbox-sandboxb-web:80" in content


def test_cleanup_stale_leaves_active_sandbox(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("live")
    mgr.register("ghost")

    removed = mgr.cleanup_stale_routes(["live"])

    assert "ghost" in removed
    assert (mgr.routes_dir / "live.yml").exists()
    assert not (mgr.routes_dir / "ghost.yml").exists()
