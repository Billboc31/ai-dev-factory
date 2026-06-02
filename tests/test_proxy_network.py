"""Tests for the shared runtime network and sandbox service discovery."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.proxy_network import (
    RUNTIME_NETWORK_NAME,
    _to_docker_safe_alias,
    sandbox_backend_urls,
    sandbox_dns_aliases,
)


def test_runtime_network_name():
    assert RUNTIME_NETWORK_NAME == "ai-dev-factory-runtime"


def test_sandbox_backend_urls_api():
    urls = sandbox_backend_urls("abc123")
    assert urls["api"] == "http://sandbox-abc123-api:8080"


def test_sandbox_backend_urls_web():
    urls = sandbox_backend_urls("abc123")
    assert urls["web"] == "http://sandbox-abc123-web:80"


def test_sandbox_backend_urls_unique_across_sandboxes():
    a = sandbox_backend_urls("aaa111")
    b = sandbox_backend_urls("bbb222")
    assert a["api"] != b["api"]
    assert a["web"] != b["web"]


def test_sandbox_backend_urls_no_host_docker_internal():
    urls = sandbox_backend_urls("xyz789")
    assert "host.docker.internal" not in urls["api"]
    assert "host.docker.internal" not in urls["web"]


def test_sandbox_backend_urls_alias_format():
    """Backend aliases are Docker-safe (lowercase) regardless of input case."""
    urls = sandbox_backend_urls("mySandbox")
    assert "sandbox-mysandbox-api" in urls["api"]
    assert "sandbox-mysandbox-web" in urls["web"]


# ── _to_docker_safe_alias ────────────────────────────────────────────────────


def test_to_docker_safe_alias_lowercase_passthrough():
    assert _to_docker_safe_alias("abc-123") == "abc-123"


def test_to_docker_safe_alias_uppercase():
    assert _to_docker_safe_alias("ABC-123") == "abc-123"


def test_to_docker_safe_alias_timestamp_separator():
    """The uppercase T in timestamp-based IDs must be lowercased."""
    assert _to_docker_safe_alias("id-20260601T194957") == "id-20260601t194957"


def test_to_docker_safe_alias_strips_invalid_chars():
    """Underscores and other non-[a-z0-9-] chars are stripped."""
    assert _to_docker_safe_alias("my_sandbox!") == "mysandbox"


def test_to_docker_safe_alias_mixed():
    assert _to_docker_safe_alias("SANDBOX-WITH-UPPER-T194957") == "sandbox-with-upper-t194957"


# ── sandbox_dns_aliases ──────────────────────────────────────────────────────


def test_sandbox_dns_aliases_keys():
    aliases = sandbox_dns_aliases("abc123")
    assert set(aliases.keys()) == {"api", "web"}


def test_sandbox_dns_aliases_normalized():
    aliases = sandbox_dns_aliases("myID-20260601T194957")
    assert aliases["api"] == "sandbox-myid-20260601t194957-api"
    assert aliases["web"] == "sandbox-myid-20260601t194957-web"


def test_sandbox_backend_urls_uppercase_normalization():
    """Acceptance criterion: uppercase sandbox IDs produce lowercase backend URLs."""
    urls = sandbox_backend_urls("SANDBOX-WITH-UPPER-T194957")
    assert urls["api"] == "http://sandbox-sandbox-with-upper-t194957-api:8080"
