"""Tests for the shared runtime network and sandbox service discovery."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.proxy_network import (
    RUNTIME_NETWORK_NAME,
    sandbox_backend_urls,
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
    """Alias names must match the docker-compose.yml aliases declaration."""
    urls = sandbox_backend_urls("mySandbox")
    assert "sandbox-mySandbox-api" in urls["api"]
    assert "sandbox-mySandbox-web" in urls["web"]
