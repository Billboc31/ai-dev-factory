"""Tests for probe_backend_from_traefik_container in proxy_route_files."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.services.proxy_route_files import probe_backend_from_traefik_container


def test_returns_empty_when_no_container_id():
    """Returns {} when TraefikManager reports no running container."""
    # TraefikManager is lazily imported inside probe_backend_from_traefik_container;
    # patch at the source module so the function-local import resolves the mock.
    with patch(
        "services.control_api.services.traefik_manager.TraefikManager"
    ) as mock_cls:
        mock_cls.return_value.infra_container_id.return_value = None
        result = probe_backend_from_traefik_container("abc123")
    assert result == {}


def test_returns_empty_when_docker_unavailable():
    """Returns {} (no exception) when Docker is not on PATH."""
    with patch("subprocess.run", side_effect=FileNotFoundError("docker not found")):
        result = probe_backend_from_traefik_container("abc123", container_id="cid123")
    assert result == {}


def test_reachable_when_wget_exits_zero():
    """Both services are 'reachable' when docker exec wget exits 0."""
    mock_ok = MagicMock()
    mock_ok.returncode = 0
    mock_ok.stdout = ""
    mock_ok.stderr = ""

    with patch("subprocess.run", return_value=mock_ok):
        result = probe_backend_from_traefik_container("abc123", container_id="cid123")

    assert result["api"] == "reachable"
    assert result["web"] == "reachable"


def test_failed_when_wget_exits_nonzero():
    """Both services show 'failed: ...' when docker exec wget exits non-zero."""
    mock_fail = MagicMock()
    mock_fail.returncode = 1
    mock_fail.stdout = ""
    mock_fail.stderr = "wget: server returned error: HTTP/1.1 502 Bad Gateway"

    with patch("subprocess.run", return_value=mock_fail):
        result = probe_backend_from_traefik_container("abc123", container_id="cid123")

    assert result["api"].startswith("failed:")
    assert result["web"].startswith("failed:")
    assert "502" in result["api"]


def test_failed_on_timeout():
    """Returns 'failed: ...' for each alias on subprocess timeout."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="docker", timeout=10)):
        result = probe_backend_from_traefik_container("abc123", container_id="cid123")

    assert result["api"].startswith("failed:")
    assert result["web"].startswith("failed:")


def test_uses_normalized_aliases():
    """Probe URLs use Docker-safe (lowercase) alias names."""
    captured_cmds: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        captured_cmds.append(cmd)
        r = MagicMock()
        r.returncode = 0
        r.stdout = ""
        r.stderr = ""
        return r

    with patch("subprocess.run", side_effect=fake_run):
        probe_backend_from_traefik_container("MyUPPER-20260601T194957", container_id="cid")

    urls = [c[-1] for c in captured_cmds]
    assert all(u == u.lower() for u in urls), f"Non-lowercase URL found: {urls}"
    assert any("sandbox-myupper-20260601t194957-api" in u for u in urls)
    assert any("sandbox-myupper-20260601t194957-web" in u for u in urls)
