"""Unit tests for ProxyManager — no Docker or Traefik required."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.proxy_manager import (
    ProxyManager,
    build_sandbox_urls,
)


@pytest.fixture()
def mgr(tmp_path):
    # ``auto_start_traefik=False`` keeps the existing pure-file tests
    # hermetic — they exercise route file writing only, not the
    # docker auto-start path. The auto-start interaction is covered
    # by ``test_register_calls_ensure_running_on_real_default`` below
    # and by the dedicated ``test_traefik_manager.py`` suite.
    return ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)


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
    ProxyManager(routes_dir=mgr.routes_dir, auto_ensure_infra=False)
    assert dashboard_file.read_text() == "custom content"
    _ = original


# ── Pure URL helper ───────────────────────────────────────────────────────────


def test_build_sandbox_urls_is_pure():
    """The helper must produce the same shape used by ``register``."""
    urls = build_sandbox_urls("abc123")
    assert urls == {
        "web": "http://sandbox-abc123.ai-dev-factory.localhost",
        "api": "http://api.sandbox-abc123.ai-dev-factory.localhost",
    }


def test_register_urls_match_build_helper(mgr):
    """Single source of truth: ``register`` returns the helper's URLs."""
    assert mgr.register("abc123", {"web": 1, "api": 2}) == build_sandbox_urls("abc123")


# ── Infra auto-ensure integration ────────────────────────────────────────────


def test_register_calls_ensure_infra_when_auto_enabled(tmp_path, monkeypatch):
    calls: list[dict] = []

    def fake_ensure(**kwargs):
        calls.append(kwargs)
        return {"reverse_proxy": True}

    import services.control_api.services.proxy_manager as pm_mod

    monkeypatch.setattr(pm_mod, "ensure_required_infra", fake_ensure)
    pm = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=True)
    pm.register("abc123", {"web": 3100, "api": 8180})
    assert len(calls) == 1
    assert list(calls[0].get("kinds", [])) == ["reverse_proxy"]


def test_register_still_writes_route_when_infra_unavailable(tmp_path, monkeypatch):
    import services.control_api.services.proxy_manager as pm_mod

    monkeypatch.setattr(
        pm_mod, "ensure_required_infra", lambda **kw: {"reverse_proxy": False}
    )
    pm = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=True)
    pm.register("abc123", {"web": 3100, "api": 8180})
    assert (pm.routes_dir / "abc123.yml").exists()


def test_register_skips_ensure_infra_when_disabled(tmp_path, monkeypatch):
    calls: list[str] = []

    def boom(**kw):
        calls.append("boom")
        return {}

    import services.control_api.services.proxy_manager as pm_mod

    monkeypatch.setattr(pm_mod, "ensure_required_infra", boom)
    pm = ProxyManager(routes_dir=tmp_path / "routes", auto_ensure_infra=False)
    pm.register("abc123", {"web": 3100, "api": 8180})
    assert calls == []


def test_proxy_routes_dir_uses_host_runtime_not_sandbox(monkeypatch, tmp_path):
    """Regression: routes must land where Traefik watches them."""
    host = tmp_path / "host-runtime"
    host.mkdir()
    sandbox = tmp_path / "sandboxes" / "x" / "runtime"
    sandbox.mkdir(parents=True)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(host))
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(sandbox))
    from services.control_api.services.infra_service_manager import (
        resolve_proxy_routes_dir,
    )

    assert resolve_proxy_routes_dir() == host / "proxy" / "routes"


# ── Stale route cleanup ──────────────────────────────────────────────────────


def test_cleanup_stale_routes_drops_files_for_unknown_sandboxes(mgr):
    mgr.register("active1", {"web": 1, "api": 2})
    mgr.register("active2", {"web": 1, "api": 2})
    mgr.register("orphan1", {"web": 1, "api": 2})
    mgr.register("orphan2", {"web": 1, "api": 2})

    removed = mgr.cleanup_stale_routes(["active1", "active2"])
    assert sorted(removed) == ["orphan1", "orphan2"]
    assert (mgr.routes_dir / "active1.yml").exists()
    assert (mgr.routes_dir / "active2.yml").exists()
    assert not (mgr.routes_dir / "orphan1.yml").exists()
    assert not (mgr.routes_dir / "orphan2.yml").exists()


def test_cleanup_stale_routes_preserves_dashboard(mgr):
    """``_``-prefixed route files belong to the infra layer (Traefik
    dashboard etc.) and must NEVER be touched by sandbox cleanup."""
    mgr.register("orphan1", {"web": 1, "api": 2})
    removed = mgr.cleanup_stale_routes([])
    assert "orphan1" in removed
    assert (mgr.routes_dir / "_dashboard.yml").exists(), (
        "infra-owned route files must survive sandbox cleanup"
    )


def test_cleanup_stale_routes_with_empty_dir_is_noop(mgr):
    # Wipe everything including _dashboard for this edge case.
    for f in mgr.routes_dir.glob("*"):
        f.unlink()
    assert mgr.cleanup_stale_routes(["whatever"]) == []


def test_cleanup_stale_routes_returns_only_removed(mgr):
    mgr.register("active", {"web": 1, "api": 2})
    mgr.register("orphan", {"web": 1, "api": 2})
    removed = mgr.cleanup_stale_routes(["active"])
    assert removed == ["orphan"]


def test_cleanup_stale_routes_does_not_remove_global_traefik(mgr, tmp_path):
    """Belt and suspenders: even an exotic infra file starting with
    ``_`` must be preserved, not just ``_dashboard.yml``."""
    (mgr.routes_dir / "_metrics.yml").write_text("dummy", encoding="utf-8")
    mgr.register("orphan", {"web": 1, "api": 2})
    mgr.cleanup_stale_routes([])
    assert (mgr.routes_dir / "_metrics.yml").exists()


# ── T158: custom host overrides ──────────────────────────────────────────────


def test_register_with_custom_web_host(mgr):
    urls = mgr.register("abc123", {"web": 3100, "api": 8180}, web_host="demo.ai-dev-factory.localhost")
    assert urls["web"] == "http://demo.ai-dev-factory.localhost"
    assert urls["api"] == "http://api.sandbox-abc123.ai-dev-factory.localhost"
    content = (mgr.routes_dir / "abc123.yml").read_text()
    assert "Host(`demo.ai-dev-factory.localhost`)" in content


def test_register_with_custom_api_host(mgr):
    urls = mgr.register("abc123", {"web": 3100, "api": 8180}, api_host="api.demo.ai-dev-factory.localhost")
    assert urls["web"] == "http://sandbox-abc123.ai-dev-factory.localhost"
    assert urls["api"] == "http://api.demo.ai-dev-factory.localhost"
    content = (mgr.routes_dir / "abc123.yml").read_text()
    assert "Host(`api.demo.ai-dev-factory.localhost`)" in content


def test_register_with_both_custom_hosts(mgr):
    urls = mgr.register(
        "abc123",
        {"web": 3100, "api": 8180},
        web_host="my-env.ai-dev-factory.localhost",
        api_host="api.my-env.ai-dev-factory.localhost",
    )
    assert urls["web"] == "http://my-env.ai-dev-factory.localhost"
    assert urls["api"] == "http://api.my-env.ai-dev-factory.localhost"
    content = (mgr.routes_dir / "abc123.yml").read_text()
    assert "Host(`my-env.ai-dev-factory.localhost`)" in content
    assert "Host(`api.my-env.ai-dev-factory.localhost`)" in content
    # Default hostnames must NOT appear in any Host() rule
    assert "sandbox-abc123.ai-dev-factory.localhost" not in content


def test_build_sandbox_urls_with_custom_hosts():
    urls = build_sandbox_urls(
        "abc123",
        web_host="my-env.ai-dev-factory.localhost",
        api_host="api.my-env.ai-dev-factory.localhost",
    )
    assert urls["web"] == "http://my-env.ai-dev-factory.localhost"
    assert urls["api"] == "http://api.my-env.ai-dev-factory.localhost"


def test_register_custom_host_still_writes_port(mgr):
    mgr.register("abc123", {"web": 9999, "api": 7777}, web_host="custom.localhost")
    content = (mgr.routes_dir / "abc123.yml").read_text()
    assert "9999" in content
    assert "7777" in content
