"""Unit tests for ProxyManager — no Docker or Traefik required."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.proxy_manager import ProxyManager


@pytest.fixture()
def mgr(tmp_path):
    return ProxyManager(routes_dir=tmp_path / "routes")


def test_register_creates_route_file(mgr):
    mgr.register("abc123", {"web": 3100, "api": 8180})
    route_file = mgr.routes_dir / "abc123.yml"
    assert route_file.exists()


def test_register_returns_correct_urls(mgr):
    urls = mgr.register("abc123", {"web": 3100, "api": 8180})
    assert urls["web"] == "http://sandbox-abc123.ai-dev-factory.localhost"
    assert urls["api"] == "http://api.sandbox-abc123.ai-dev-factory.localhost"


def test_register_route_file_contains_hostnames(mgr):
    mgr.register("abc123", {"web": 3100, "api": 8180})
    content = (mgr.routes_dir / "abc123.yml").read_text()
    assert "sandbox-abc123.ai-dev-factory.localhost" in content
    assert "api.sandbox-abc123.ai-dev-factory.localhost" in content


def test_register_route_file_contains_ports(mgr):
    mgr.register("abc123", {"web": 3100, "api": 8180})
    content = (mgr.routes_dir / "abc123.yml").read_text()
    assert "3100" in content
    assert "8180" in content


def test_unregister_removes_route_file(mgr):
    mgr.register("abc123", {"web": 3100, "api": 8180})
    mgr.unregister("abc123")
    assert not (mgr.routes_dir / "abc123.yml").exists()


def test_unregister_missing_file_is_safe(mgr):
    mgr.unregister("nonexistent")


def test_register_is_idempotent(mgr):
    mgr.register("abc123", {"web": 3100, "api": 8180})
    urls = mgr.register("abc123", {"web": 3200, "api": 8280})
    content = (mgr.routes_dir / "abc123.yml").read_text()
    assert "3200" in content
    assert urls["web"] == "http://sandbox-abc123.ai-dev-factory.localhost"


def test_hostnames_unique_across_sandboxes(mgr):
    urls1 = mgr.register("aaa111", {"web": 3100, "api": 8180})
    urls2 = mgr.register("bbb222", {"web": 3200, "api": 8280})
    assert urls1["web"] != urls2["web"]
    assert urls1["api"] != urls2["api"]


def test_concurrent_sandboxes_have_separate_files(mgr):
    mgr.register("aaa111", {"web": 3100, "api": 8180})
    mgr.register("bbb222", {"web": 3200, "api": 8280})
    assert (mgr.routes_dir / "aaa111.yml").exists()
    assert (mgr.routes_dir / "bbb222.yml").exists()


def test_unregister_only_removes_target_sandbox(mgr):
    mgr.register("aaa111", {"web": 3100, "api": 8180})
    mgr.register("bbb222", {"web": 3200, "api": 8280})
    mgr.unregister("aaa111")
    assert not (mgr.routes_dir / "aaa111.yml").exists()
    assert (mgr.routes_dir / "bbb222.yml").exists()


def test_init_seeds_dashboard_route(mgr):
    dashboard_file = mgr.routes_dir / "_dashboard.yml"
    assert dashboard_file.exists()
    assert "traefik.ai-dev-factory.localhost" in dashboard_file.read_text()


def test_init_does_not_overwrite_existing_dashboard(mgr):
    dashboard_file = mgr.routes_dir / "_dashboard.yml"
    original = dashboard_file.read_text()
    dashboard_file.write_text("custom content", encoding="utf-8")
    ProxyManager(routes_dir=mgr.routes_dir)
    assert dashboard_file.read_text() == "custom content"
    _ = original
