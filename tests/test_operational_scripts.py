"""End-to-end and structural tests for ``.ai-dev-factory/scripts/*``.

The scripts must work in two modes:

1. **Main runtime** — ports come from ``deploy/.env`` or fall back to
   the documented defaults (``8080`` / ``3000`` / ``8090``).
2. **Sandbox runs** — ``tools/agent_runner/run_sandbox.py`` allocates
   isolated ports and pretty URLs and injects them via the process
   env (``API_PORT``, ``WEB_PORT``, ``AI_DEV_FACTORY_SUPERVISOR_*``,
   ``SANDBOX_WEB_URL`` / ``SANDBOX_API_URL``).

Two key invariants tested here:

* The healthcheck prefers ``SANDBOX_WEB_URL`` / ``SANDBOX_API_URL``
  when set so it validates the SAME endpoint a human will see, not a
  backdoor on a host port. Without this preference, a broken Traefik
  registration would still pass healthcheck via the direct port —
  a false positive that hides real proxy-deploy failures.

* The supervisor probe uses ``AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL``
  (loopback) rather than ``AI_DEV_FACTORY_SUPERVISOR_URL`` (which
  uses ``host.docker.internal``, not resolvable from host shells).
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = _REPO_ROOT / ".ai-dev-factory" / "scripts"
_START_SH = _SCRIPTS_DIR / "start.sh"
_HEALTHCHECK_SH = _SCRIPTS_DIR / "healthcheck.sh"


# ── Static shape ─────────────────────────────────────────────────────────────


def test_start_sh_exists():
    assert _START_SH.exists()


def test_healthcheck_sh_exists():
    assert _HEALTHCHECK_SH.exists()


@pytest.mark.parametrize(
    "script_path", [_START_SH, _HEALTHCHECK_SH], ids=["start.sh", "healthcheck.sh"]
)
@pytest.mark.parametrize(
    "var",
    [
        "API_PORT", "WEB_PORT",
        "AI_DEV_FACTORY_SUPERVISOR_PORT",
        "AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL",
        "SANDBOX_API_URL", "SANDBOX_WEB_URL",
    ],
)
def test_scripts_reference_env_vars(script_path: Path, var: str):
    text = script_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"\$\{{{var}\b|\b{var}=")
    assert pattern.search(text), (
        f"{script_path.name} must reference {var}"
    )


@pytest.mark.parametrize(
    "script_path", [_START_SH, _HEALTHCHECK_SH], ids=["start.sh", "healthcheck.sh"]
)
@pytest.mark.parametrize("hostport", [
    "localhost:8080", "localhost:3000", "127.0.0.1:8090",
    "localhost:8090", "0.0.0.0:8080",
])
def test_scripts_have_no_hardcoded_port_urls(script_path: Path, hostport: str):
    """Hardcoded ``localhost:8080``-style tokens would silently
    downgrade sandbox runs to the main-runtime ports — a false
    positive. ``${VAR:-default}`` expansions ARE allowed (those are
    the documented main-runtime fallback)."""
    text = script_path.read_text(encoding="utf-8")
    # Strip bash comments and parameter-expansion defaults before scanning.
    no_comments = re.sub(r"(?m)(?<![#${])#.*$", "", text)
    no_defaults = re.sub(r"\$\{[A-Za-z_][A-Za-z0-9_]*:-[^}]*\}", "", no_comments)
    assert hostport not in no_defaults, (
        f"{script_path.name} contains hardcoded '{hostport}' — use the "
        f"env expansions instead"
    )


def test_scripts_implement_sandbox_precedence_pattern():
    """Both scripts must snapshot inbound env BEFORE sourcing
    ``deploy/.env`` and restore it AFTER. Otherwise a deploy/.env
    that happens to set API_PORT=8080 would silently overwrite the
    sandbox-injected value."""
    for path in (_START_SH, _HEALTHCHECK_SH):
        text = path.read_text(encoding="utf-8")
        for var in ("__SB_API_PORT", "__SB_WEB_PORT", "__SB_SUPERVISOR_HEALTH_URL"):
            assert var in text, f"{path.name} missing sandbox-precedence snapshot for {var}"
        snapshot_pos = text.index("__SB_API_PORT")
        # Match the actual source line, not a mention in the comment block
        # above it. ``[ -f deploy/.env ] && source deploy/.env`` is the
        # canonical pattern.
        source_pos = text.index("[ -f deploy/.env ] && source deploy/.env")
        assert snapshot_pos < source_pos, (
            f"{path.name}: env snapshot must precede `source deploy/.env`"
        )
        restore_pos = text.rindex('"${__SB_API_PORT')
        assert restore_pos > source_pos


# ── Healthcheck probe shape ───────────────────────────────────────────────────


def test_healthcheck_probes_use_supervisor_health_url():
    """Host-side scripts must probe the loopback supervisor URL, not
    the docker-internal one. Without this fix, every healthcheck on a
    macOS / Linux host (where ``host.docker.internal`` is unresolvable
    from a host shell) would fail with NXDOMAIN."""
    text = _HEALTHCHECK_SH.read_text(encoding="utf-8")
    assert "AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL" in text
    # The probe line for supervisor must use the HEALTH_URL.
    assert re.search(
        r'probe\s+"supervisor"\s+"\$\{AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL\}/health"',
        text,
    ), "healthcheck.sh supervisor probe must use ${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL}"


def test_healthcheck_prefers_sandbox_urls_over_direct_ports():
    """When ``SANDBOX_API_URL`` is set, the api probe must use it;
    otherwise the probe falls back to direct ``localhost:${API_PORT}``."""
    text = _HEALTHCHECK_SH.read_text(encoding="utf-8")
    # Branch present for api
    assert re.search(r'if\s*\[\s*-n\s*"\$SANDBOX_API_URL"\s*\]', text), text
    # Both forms appear (preferred + fallback)
    assert "${SANDBOX_API_URL}/health" in text
    assert "http://localhost:${API_PORT}/health" in text
    # Same for web
    assert re.search(r'if\s*\[\s*-n\s*"\$SANDBOX_WEB_URL"\s*\]', text)
    assert "${SANDBOX_WEB_URL}" in text
    assert "http://localhost:${WEB_PORT}" in text


def test_start_sh_announces_sandbox_urls_when_set():
    text = _START_SH.read_text(encoding="utf-8")
    assert "SANDBOX_API_URL" in text
    assert "SANDBOX_WEB_URL" in text
    # The fallback to direct ports must still exist for main runtime.
    assert "http://localhost:${API_PORT}" in text
    assert "http://localhost:${WEB_PORT}" in text


# ── Runtime behaviour (bash subshell) ─────────────────────────────────────────
#
# Boot the precedence block in a controlled bash subshell with a
# stub ``deploy/.env`` and assert the resolved values match the
# precedence rule.


def _resolution_block(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    end_idx = text.index("unset __SB_API_URL __SB_WEB_URL")
    end_idx = text.index("\n", end_idx) + 1
    return text[:end_idx]


def _resolve(
    block: str,
    deploy_env: str | None,
    env: dict[str, str],
    tmp_path: Path,
) -> dict[str, str]:
    project = tmp_path / "project"
    (project / "deploy").mkdir(parents=True)
    if deploy_env is not None:
        (project / "deploy" / ".env").write_text(deploy_env, encoding="utf-8")
    (project / ".ai-dev-factory" / "scripts").mkdir(parents=True)
    script = project / ".ai-dev-factory" / "scripts" / "_block.sh"
    script.write_text(
        block + (
            'printf "API_PORT=%s\\n" "${API_PORT:-}"\n'
            'printf "WEB_PORT=%s\\n" "${WEB_PORT:-}"\n'
            'printf "SUP_PORT=%s\\n" "${AI_DEV_FACTORY_SUPERVISOR_PORT:-}"\n'
            'printf "SUP_URL=%s\\n" "${AI_DEV_FACTORY_SUPERVISOR_URL:-}"\n'
            'printf "SUP_HEALTH=%s\\n" "${AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL:-}"\n'
            'printf "SB_API_URL=%s\\n" "${SANDBOX_API_URL:-}"\n'
            'printf "SB_WEB_URL=%s\\n" "${SANDBOX_WEB_URL:-}"\n'
        ),
        encoding="utf-8",
    )
    result = subprocess.run(
        ["bash", str(script)],
        env={**os.environ, **env, "PATH": os.environ.get("PATH", "")},
        capture_output=True, text=True, check=True, timeout=10,
    )
    out: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            out[k] = v
    return out


def test_resolution_main_runtime_defaults(tmp_path):
    """No injected env, no deploy/.env → documented defaults; sandbox
    URLs stay empty so the healthcheck falls back to direct ports."""
    out = _resolve(
        _resolution_block(_START_SH),
        deploy_env=None,
        env={
            "API_PORT": "", "WEB_PORT": "",
            "AI_DEV_FACTORY_SUPERVISOR_PORT": "",
            "AI_DEV_FACTORY_SUPERVISOR_URL": "",
            "AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL": "",
            "SANDBOX_API_URL": "", "SANDBOX_WEB_URL": "",
        },
        tmp_path=tmp_path,
    )
    assert out["API_PORT"] == "8080"
    assert out["WEB_PORT"] == "3000"
    assert out["SUP_PORT"] == "8090"
    assert out["SUP_HEALTH"] == "http://127.0.0.1:8090"
    assert out["SB_API_URL"] == ""
    assert out["SB_WEB_URL"] == ""


def test_resolution_sandbox_injected_urls(tmp_path):
    """Sandbox env carries pretty URLs + host-side supervisor URL."""
    env = {
        "API_PORT": "8180", "WEB_PORT": "3100",
        "AI_DEV_FACTORY_SUPERVISOR_PORT": "8091",
        "AI_DEV_FACTORY_SUPERVISOR_URL": "http://host.docker.internal:8091",
        "AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL": "http://127.0.0.1:8091",
        "SANDBOX_API_URL": "http://api.sandbox-xyz.ai-dev-factory.localhost",
        "SANDBOX_WEB_URL": "http://sandbox-xyz.ai-dev-factory.localhost",
    }
    out = _resolve(_resolution_block(_START_SH), None, env, tmp_path)
    assert out["API_PORT"] == "8180"
    assert out["WEB_PORT"] == "3100"
    assert out["SUP_PORT"] == "8091"
    assert out["SUP_URL"] == "http://host.docker.internal:8091"
    assert out["SUP_HEALTH"] == "http://127.0.0.1:8091"
    assert out["SB_API_URL"] == "http://api.sandbox-xyz.ai-dev-factory.localhost"
    assert out["SB_WEB_URL"] == "http://sandbox-xyz.ai-dev-factory.localhost"


def test_resolution_sandbox_beats_deploy_env(tmp_path):
    """deploy/.env API_PORT=8080 must NOT override a sandbox API_PORT=8180."""
    out = _resolve(
        _resolution_block(_START_SH),
        deploy_env=(
            "API_PORT=8080\nWEB_PORT=3000\n"
            "AI_DEV_FACTORY_SUPERVISOR_PORT=8090\n"
            "AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL=http://127.0.0.1:8090\n"
        ),
        env={
            "API_PORT": "8180", "WEB_PORT": "3100",
            "AI_DEV_FACTORY_SUPERVISOR_PORT": "8091",
            "AI_DEV_FACTORY_SUPERVISOR_URL": "http://host.docker.internal:8091",
            "AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL": "http://127.0.0.1:8091",
            "SANDBOX_API_URL": "http://api.sandbox-xyz.ai-dev-factory.localhost",
            "SANDBOX_WEB_URL": "http://sandbox-xyz.ai-dev-factory.localhost",
        },
        tmp_path=tmp_path,
    )
    assert out["API_PORT"] == "8180"
    assert out["SUP_HEALTH"] == "http://127.0.0.1:8091"
    assert out["SB_API_URL"] == "http://api.sandbox-xyz.ai-dev-factory.localhost"


def test_resolution_healthcheck_matches_start(tmp_path):
    """Both scripts must resolve identically — otherwise start.sh would
    announce one set of URLs while healthcheck.sh would probe another."""
    env = {
        "API_PORT": "8180", "WEB_PORT": "3100",
        "AI_DEV_FACTORY_SUPERVISOR_PORT": "8091",
        "AI_DEV_FACTORY_SUPERVISOR_URL": "http://host.docker.internal:8091",
        "AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL": "http://127.0.0.1:8091",
        "SANDBOX_API_URL": "http://api.sandbox-xyz.ai-dev-factory.localhost",
        "SANDBOX_WEB_URL": "http://sandbox-xyz.ai-dev-factory.localhost",
    }
    a = _resolve(_resolution_block(_START_SH), None, env, tmp_path / "a")
    b = _resolve(_resolution_block(_HEALTHCHECK_SH), None, env, tmp_path / "b")
    assert a == b, f"start/healthcheck resolve differently: {a} vs {b}"
