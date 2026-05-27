"""Integration test for PROXY_INFRA_FAIL classification in healthcheck.sh."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_HEALTHCHECK = _REPO_ROOT / ".ai-dev-factory" / "scripts" / "healthcheck.sh"


@pytest.mark.integration
def test_healthcheck_emits_proxy_infra_fail(tmp_path):
    """healthcheck.sh emits PROXY_INFRA_FAIL when SANDBOX_API_URL is set but Traefik is not up."""
    fake_curl = tmp_path / "curl"
    fake_curl.write_text("#!/usr/bin/env bash\nexit 1\n")
    fake_curl.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "SANDBOX_API_URL": "http://api.sandbox-test.ai-dev-factory.localhost",
        "SANDBOX_WEB_URL": "http://sandbox-test.ai-dev-factory.localhost",
        "SANDBOX_ID": "test",
        "AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL": "http://127.0.0.1:19999",
    }

    result = subprocess.run(
        ["bash", str(_HEALTHCHECK)],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(tmp_path),
    )

    assert "PROXY_INFRA_FAIL" in result.stdout
