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
    return ProxyManager(routes_dir=tmp_path / "routes", auto_start_traefik=False)


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
    ProxyManager(routes_dir=mgr.routes_dir, auto_start_traefik=False)
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


# ── Traefik auto-start integration ───────────────────────────────────────────
#
# Production callers want `register` to make sure Traefik is up before
# writing the route file, so the URL the dashboard surfaces is usable
# immediately. These tests exercise the wiring with a stub
# TraefikManager so the test stays hermetic (no real docker).


class _StubTraefik:
    def __init__(self, ok: bool = True):
        self.calls: list[str] = []
        self.ok = ok

    def ensure_running(self, timeout: float = 15.0) -> bool:
        self.calls.append("ensure_running")
        return self.ok


def test_register_calls_ensure_running_when_auto_start_enabled(tmp_path):
    stub = _StubTraefik()
    pm = ProxyManager(
        routes_dir=tmp_path / "routes",
        traefik_manager=stub,
        auto_start_traefik=True,
    )
    pm.register("abc123", {"web": 3100, "api": 8180})
    assert stub.calls == ["ensure_running"], (
        "auto_start=True must trigger ensure_running before route write"
    )


def test_register_still_writes_route_when_traefik_unavailable(tmp_path):
    """Best-effort semantics: a failed auto-start logs a warning but
    still writes the route file so it picks up once the operator
    brings Traefik up manually."""
    stub = _StubTraefik(ok=False)
    pm = ProxyManager(
        routes_dir=tmp_path / "routes",
        traefik_manager=stub,
        auto_start_traefik=True,
    )
    pm.register("abc123", {"web": 3100, "api": 8180})
    assert (pm.routes_dir / "abc123.yml").exists()


def test_register_skips_ensure_running_when_disabled(tmp_path):
    """``auto_start_traefik=False`` is the test/CI escape hatch — it
    must not touch the (probably non-existent) docker daemon."""
    stub = _StubTraefik()
    pm = ProxyManager(
        routes_dir=tmp_path / "routes",
        traefik_manager=stub,
        auto_start_traefik=False,
    )
    pm.register("abc123", {"web": 3100, "api": 8180})
    assert stub.calls == []


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
