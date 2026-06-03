"""Tests for the runtime network attachment block in start.sh.

Runs start.sh with a fake docker binary to verify:
  - containers not on ai-dev-factory-runtime get connected with the correct alias
  - re-runs are idempotent when containers are already connected
  - connect returning "already exists" is treated as idempotent (deploy succeeds)
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_START_SH = _REPO_ROOT / ".ai-dev-factory" / "scripts" / "start.sh"
_RUNTIME_NETWORK = "ai-dev-factory-runtime"
_SANDBOX_ID = "testid123456ab"
_COMPOSE_PROJECT = f"sandbox-{_SANDBOX_ID}"


def _write_fake_docker(bin_dir: Path) -> None:
    """Write a stateful fake docker binary.

    Behaviour is controlled by env vars set on the start.sh subprocess:
      FAKE_NETWORKS        space-separated network names returned by 'docker inspect'
      FAKE_CONNECT_ERROR   stderr text for 'docker network connect'; empty → success
      FAKE_DOCKER_LOG      path where every docker invocation is appended

    The binary returns distinct container IDs for api (containerapi123456) and
    web (containerweb654321) so that per-container connect markers are isolated.
    """
    script = f"""\
#!/usr/bin/env bash
LOG_FILE="${{FAKE_DOCKER_LOG:-/dev/null}}"
echo "$@" >> "$LOG_FILE"
CMD="$*"

if echo "$CMD" | grep -qE "compose.*config"; then
  printf 'sandbox-{_SANDBOX_ID}-api\\nsandbox-{_SANDBOX_ID}-web\\n'
  exit 0
elif echo "$CMD" | grep -qE "compose.*up"; then
  exit 0
elif echo "$CMD" | grep -qE "compose.*ps"; then
  if echo "$CMD" | grep -q " api$"; then
    echo "containerapi123456"
  else
    echo "containerweb654321"
  fi
  exit 0
elif echo "$CMD" | grep -qE "^inspect "; then
  CONTAINER_ID=$(echo "$CMD" | awk '{{print $2}}')
  MARKER="$LOG_FILE.connected.$CONTAINER_ID"
  if [ -f "$MARKER" ]; then
    printf '%s ' "ai-dev-factory-runtime" "${{FAKE_NETWORKS:-}}"
    printf '\\n'
  else
    printf '%s\\n' "${{FAKE_NETWORKS:-}}"
  fi
  exit 0
elif echo "$CMD" | grep -q "network connect"; then
  CONTAINER_ID=$(echo "$CMD" | awk '{{print $NF}}')
  MARKER="$LOG_FILE.connected.$CONTAINER_ID"
  _err="${{FAKE_CONNECT_ERROR:-}}"
  if [ -n "$_err" ]; then
    echo "$_err" >&2
    if echo "$_err" | grep -qiE "already exists|endpoint with name"; then
      touch "$MARKER"
    fi
    exit 1
  fi
  touch "$MARKER"
  exit 0
fi
exit 0
"""
    docker = bin_dir / "docker"
    docker.write_text(script, encoding="utf-8")
    docker.chmod(docker.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture()
def project_root(tmp_path):
    root = tmp_path / "project"
    root.mkdir()
    scripts_dir = root / ".ai-dev-factory" / "scripts"
    scripts_dir.mkdir(parents=True)
    shutil.copy2(str(_START_SH), str(scripts_dir / "start.sh"))
    return root


@pytest.fixture()
def fake_bin(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_fake_docker(bin_dir)
    return bin_dir


def _run(project_root: Path, fake_bin: Path, **extra_env: str) -> subprocess.CompletedProcess:
    log = fake_bin / "docker.log"
    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "SANDBOX_ID": _SANDBOX_ID,
        "COMPOSE_PROJECT_NAME": _COMPOSE_PROJECT,
        "AI_DEV_FACTORY_SUPERVISOR_ALREADY_STARTED": "1",
        "FAKE_DOCKER_LOG": str(log),
        **extra_env,
    }
    return subprocess.run(
        ["bash", str(project_root / ".ai-dev-factory" / "scripts" / "start.sh")],
        capture_output=True,
        text=True,
        cwd=str(project_root),
        env=env,
    )


def _log(fake_bin: Path) -> str:
    p = fake_bin / "docker.log"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def test_connects_containers_missing_runtime_network(project_root, fake_bin):
    """api and web containers not on runtime network → docker network connect called."""
    result = _run(
        project_root,
        fake_bin,
        FAKE_NETWORKS=f"sandbox-{_SANDBOX_ID}_default",
        FAKE_CONNECT_ERROR="",
    )
    log = _log(fake_bin)

    assert result.returncode == 0, result.stderr
    assert "network connect" in log
    assert f"--alias sandbox-{_SANDBOX_ID}-api" in log
    assert f"--alias sandbox-{_SANDBOX_ID}-web" in log
    assert f"ai-dev-factory-runtime" in log


def test_skips_connect_when_already_on_runtime_network(project_root, fake_bin):
    """Containers already on runtime network → docker network connect not called."""
    result = _run(
        project_root,
        fake_bin,
        FAKE_NETWORKS=f"{_RUNTIME_NETWORK} sandbox-{_SANDBOX_ID}_default",
        FAKE_CONNECT_ERROR="",
    )
    log = _log(fake_bin)

    assert result.returncode == 0, result.stderr
    assert "network connect" not in log
    assert "already on" in result.stdout


def test_idempotent_on_already_connected_docker_error(project_root, fake_bin):
    """connect returning 'already exists' is treated as idempotent — deploy succeeds."""
    connect_err = (
        "Error response from daemon: endpoint with name containerabc123 "
        "already exists in network ai-dev-factory-runtime"
    )
    result = _run(
        project_root,
        fake_bin,
        FAKE_NETWORKS=f"sandbox-{_SANDBOX_ID}_default",
        FAKE_CONNECT_ERROR=connect_err,
    )

    assert result.returncode == 0, result.stderr
    assert "already connected" in result.stdout
