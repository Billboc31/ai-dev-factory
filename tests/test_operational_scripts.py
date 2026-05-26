"""End-to-end and structural tests for ``.ai-dev-factory/scripts/*``.

The scripts must work in two modes:

1. **Main runtime** — ports come from ``deploy/.env`` or fall back to
   the documented defaults (``8080`` / ``3000`` / ``8090``).
2. **Sandbox runs** — ``tools/agent_runner/run_sandbox.py`` allocates
   isolated ports per sandbox and injects them via the process env
   (``API_PORT``, ``WEB_PORT``, ``AI_DEV_FACTORY_SUPERVISOR_PORT``,
   ``AI_DEV_FACTORY_SUPERVISOR_URL``).

If the scripts hardcode ``localhost:8080`` instead of expanding the
env vars, sandbox healthchecks silently probe the MAIN runtime and
report a false-positive green light. These tests pin both the
static shape and the runtime resolution behaviour.
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
    assert _START_SH.exists(), f"missing {_START_SH}"


def test_healthcheck_sh_exists():
    assert _HEALTHCHECK_SH.exists(), f"missing {_HEALTHCHECK_SH}"


@pytest.mark.parametrize(
    "script_path", [_START_SH, _HEALTHCHECK_SH], ids=["start.sh", "healthcheck.sh"]
)
@pytest.mark.parametrize(
    "var", ["API_PORT", "WEB_PORT", "AI_DEV_FACTORY_SUPERVISOR_PORT"]
)
def test_scripts_reference_env_vars(script_path: Path, var: str):
    text = script_path.read_text(encoding="utf-8")
    # Use a strict regex so we don't false-match comments alone — the
    # script must actually expand ``${VAR…}`` or assign ``VAR=`` so the
    # value flows into emitted URLs / probes.
    pattern = re.compile(rf"\$\{{{var}\b|\b{var}=")
    assert pattern.search(text), (
        f"{script_path.name} must reference {var} (currently doesn't)"
    )


@pytest.mark.parametrize(
    "script_path", [_START_SH, _HEALTHCHECK_SH], ids=["start.sh", "healthcheck.sh"]
)
@pytest.mark.parametrize("hostport", [
    "localhost:8080", "localhost:3000", "127.0.0.1:8090",
    "localhost:8090", "0.0.0.0:8080",
])
def test_scripts_have_no_hardcoded_port_urls(script_path: Path, hostport: str):
    """Any literal `localhost:8080`-style token would silently downgrade
    sandbox runs to the main-runtime ports — a false positive."""
    text = script_path.read_text(encoding="utf-8")
    # Strip bash comments first so doc text can reference the defaults.
    no_comments = re.sub(r"(?m)(?<![#${])#.*$", "", text)
    assert hostport not in no_comments, (
        f"{script_path.name} contains hardcoded '{hostport}' — use the "
        f"env expansions (${{API_PORT}}, ${{WEB_PORT}}, "
        f"${{AI_DEV_FACTORY_SUPERVISOR_URL}}) instead"
    )


def test_scripts_implement_sandbox_precedence_pattern():
    """Both scripts must snapshot inbound env BEFORE sourcing
    ``deploy/.env`` and restore it AFTER. Otherwise a deploy/.env that
    happens to set API_PORT=8080 would silently overwrite the
    sandbox-injected value."""
    for path in (_START_SH, _HEALTHCHECK_SH):
        text = path.read_text(encoding="utf-8")
        assert "__SB_API_PORT" in text, (
            f"{path.name} missing sandbox-precedence snapshot for API_PORT"
        )
        assert "__SB_WEB_PORT" in text, (
            f"{path.name} missing sandbox-precedence snapshot for WEB_PORT"
        )
        # The snapshot must appear BEFORE deploy/.env is sourced.
        snapshot_pos = text.index("__SB_API_PORT")
        source_pos = text.index("source deploy/.env")
        assert snapshot_pos < source_pos, (
            f"{path.name}: env snapshot must precede `source deploy/.env`"
        )
        # Restoration: the snapshot is consumed AFTER the source.
        restore_pos = text.rindex('"${__SB_API_PORT')
        assert restore_pos > source_pos, (
            f"{path.name}: snapshot must be restored after sourcing deploy/.env"
        )


# ── Runtime behaviour (bash subshell) ─────────────────────────────────────────
#
# Boot the precedence block in a controlled bash subshell with a stub
# ``deploy/.env`` and assert the resolved values match the sandbox
# precedence rule. We don't run the full script (would try to spawn
# the supervisor + docker), so we extract the resolution block.


def _resolution_block(path: Path) -> str:
    """Return the env-resolution prelude of *path* (everything up to and
    including ``unset __SB_…``)."""
    text = path.read_text(encoding="utf-8")
    end = text.index("unset __SB_API_PORT")
    end = text.index("\n", end) + 1
    return text[:end]


def _resolve_in_bash(
    block: str,
    deploy_env: str | None,
    env: dict[str, str],
    tmp_path: Path,
) -> dict[str, str]:
    """Source *block* under *env* with an optional stub deploy/.env and
    return the resolved values."""
    project_root = tmp_path / "project"
    (project_root / "deploy").mkdir(parents=True)
    if deploy_env is not None:
        (project_root / "deploy" / ".env").write_text(deploy_env, encoding="utf-8")
    (project_root / ".ai-dev-factory" / "scripts").mkdir(parents=True)
    script = project_root / ".ai-dev-factory" / "scripts" / "_block.sh"
    # Tail emits the resolved values for the test to parse.
    script.write_text(
        block + (
            'printf "API_PORT=%s\\n" "${API_PORT:-}"\n'
            'printf "WEB_PORT=%s\\n" "${WEB_PORT:-}"\n'
            'printf "SUP_PORT=%s\\n" "${AI_DEV_FACTORY_SUPERVISOR_PORT:-}"\n'
            'printf "SUP_URL=%s\\n" "${AI_DEV_FACTORY_SUPERVISOR_URL:-}"\n'
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


def test_resolution_uses_env_when_sandbox_injects_ports(tmp_path):
    """Sandbox env vars present, no deploy/.env → env wins."""
    block = _resolution_block(_START_SH)
    resolved = _resolve_in_bash(
        block,
        deploy_env=None,
        env={
            "API_PORT": "8180",
            "WEB_PORT": "3100",
            "AI_DEV_FACTORY_SUPERVISOR_PORT": "8190",
            "AI_DEV_FACTORY_SUPERVISOR_URL": "http://host.docker.internal:8190",
        },
        tmp_path=tmp_path,
    )
    assert resolved["API_PORT"] == "8180"
    assert resolved["WEB_PORT"] == "3100"
    assert resolved["SUP_PORT"] == "8190"
    assert resolved["SUP_URL"] == "http://host.docker.internal:8190"


def test_resolution_uses_defaults_when_no_env_and_no_deploy_env(tmp_path):
    """Plain main runtime, no overrides → documented defaults."""
    block = _resolution_block(_START_SH)
    resolved = _resolve_in_bash(
        block, deploy_env=None,
        env={
            "API_PORT": "", "WEB_PORT": "",
            "AI_DEV_FACTORY_SUPERVISOR_PORT": "",
            "AI_DEV_FACTORY_SUPERVISOR_URL": "",
        },
        tmp_path=tmp_path,
    )
    assert resolved["API_PORT"] == "8080"
    assert resolved["WEB_PORT"] == "3000"
    assert resolved["SUP_PORT"] == "8090"
    assert resolved["SUP_URL"] == "http://127.0.0.1:8090"


def test_resolution_reads_deploy_env_when_no_sandbox(tmp_path):
    """Main runtime with deploy/.env overrides → deploy/.env wins over
    documented defaults."""
    block = _resolution_block(_START_SH)
    resolved = _resolve_in_bash(
        block,
        deploy_env="API_PORT=9000\nWEB_PORT=9001\n",
        env={
            "API_PORT": "", "WEB_PORT": "",
            "AI_DEV_FACTORY_SUPERVISOR_PORT": "",
            "AI_DEV_FACTORY_SUPERVISOR_URL": "",
        },
        tmp_path=tmp_path,
    )
    assert resolved["API_PORT"] == "9000"
    assert resolved["WEB_PORT"] == "9001"


def test_resolution_sandbox_beats_deploy_env(tmp_path):
    """Sandbox-injected env MUST win over deploy/.env values. This is the
    regression the user reported: deploy/.env had API_PORT=8080 and was
    silently overriding the sandbox's allocated 8180."""
    block = _resolution_block(_START_SH)
    resolved = _resolve_in_bash(
        block,
        deploy_env="API_PORT=8080\nWEB_PORT=3000\nAI_DEV_FACTORY_SUPERVISOR_PORT=8090\n",
        env={
            "API_PORT": "8180",
            "WEB_PORT": "3100",
            "AI_DEV_FACTORY_SUPERVISOR_PORT": "8190",
            "AI_DEV_FACTORY_SUPERVISOR_URL": "http://host.docker.internal:8190",
        },
        tmp_path=tmp_path,
    )
    assert resolved["API_PORT"] == "8180", (
        "sandbox-injected API_PORT must win over deploy/.env — "
        "otherwise sandboxes silently downgrade to main runtime"
    )
    assert resolved["WEB_PORT"] == "3100"
    assert resolved["SUP_PORT"] == "8190"
    assert resolved["SUP_URL"] == "http://host.docker.internal:8190"


def test_healthcheck_resolution_matches_start(tmp_path):
    """The two scripts must resolve to the SAME values from the SAME
    env. Mismatched resolution would mean start.sh announces one set
    of URLs while healthcheck.sh probes another."""
    env = {
        "API_PORT": "8180",
        "WEB_PORT": "3100",
        "AI_DEV_FACTORY_SUPERVISOR_PORT": "8190",
        "AI_DEV_FACTORY_SUPERVISOR_URL": "http://host.docker.internal:8190",
    }
    a = _resolve_in_bash(_resolution_block(_START_SH), None, env, tmp_path / "a")
    b = _resolve_in_bash(_resolution_block(_HEALTHCHECK_SH), None, env, tmp_path / "b")
    assert a == b, f"start.sh and healthcheck.sh resolve differently: {a} vs {b}"


def test_healthcheck_probes_use_env_expansions():
    """The actual probe lines must reference the env-driven URL forms."""
    text = _HEALTHCHECK_SH.read_text(encoding="utf-8")
    # API probe
    assert re.search(r'probe\s+"api"\s+"http://localhost:\$\{API_PORT\}/health"', text), (
        "healthcheck.sh api probe must use ${API_PORT}"
    )
    # Web probe
    assert re.search(r'probe\s+"web"\s+"http://localhost:\$\{WEB_PORT\}"', text), (
        "healthcheck.sh web probe must use ${WEB_PORT}"
    )
    # Supervisor probe via resolved URL
    assert re.search(
        r'probe\s+"supervisor"\s+"\$\{AI_DEV_FACTORY_SUPERVISOR_URL\}/health"', text
    ), "healthcheck.sh supervisor probe must use ${AI_DEV_FACTORY_SUPERVISOR_URL}"
