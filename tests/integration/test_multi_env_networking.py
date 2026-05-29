"""Integration: two sandboxes running concurrently share the ingress network
without hostname collisions and each gets a unique, deterministic backend URL.

No real Docker required — ProxyManager route-file logic is exercised end-to-end;
alias URL correctness is the contract under test.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.control_api.services.proxy_manager import ProxyManager
from services.control_api.services.proxy_network import sandbox_backend_urls


def test_two_sandboxes_have_unique_hostnames(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    urls_a = mgr.register("sandbox01")
    urls_b = mgr.register("sandbox02")

    assert urls_a["web"] != urls_b["web"]
    assert urls_a["api"] != urls_b["api"]


def test_two_sandboxes_have_unique_backend_aliases():
    a = sandbox_backend_urls("sandbox01")
    b = sandbox_backend_urls("sandbox02")

    assert a["api"] != b["api"]
    assert a["web"] != b["web"]
    assert "sandbox01" in a["api"]
    assert "sandbox02" in b["api"]


def test_two_sandboxes_each_get_route_file(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("sandbox01")
    mgr.register("sandbox02")

    assert (mgr.routes_dir / "sandbox01.yml").exists()
    assert (mgr.routes_dir / "sandbox02.yml").exists()


def test_route_files_reference_correct_aliases(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("sandbox01")
    mgr.register("sandbox02")

    content_a = (mgr.routes_dir / "sandbox01.yml").read_text()
    content_b = (mgr.routes_dir / "sandbox02.yml").read_text()

    assert "sandbox-sandbox01-api:8080" in content_a
    assert "sandbox-sandbox01-web:80" in content_a
    assert "sandbox-sandbox02-api:8080" in content_b
    assert "sandbox-sandbox02-web:80" in content_b

    # No cross-contamination
    assert "sandbox02" not in content_a
    assert "sandbox01" not in content_b


def test_no_host_docker_internal_in_routes(tmp_path):
    mgr = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    mgr.register("sandbox01")
    mgr.register("sandbox02")

    for name in ("sandbox01", "sandbox02"):
        content = (mgr.routes_dir / f"{name}.yml").read_text()
        assert "host.docker.internal" not in content
