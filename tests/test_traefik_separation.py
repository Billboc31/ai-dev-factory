"""Architectural tests for the Traefik / sandbox separation.

These tests pin a single invariant: the root project compose file
(``docker-compose.yml``) must NOT contain a ``traefik`` service.
That separation is what stops every sandbox ``docker compose up``
from trying to bring up a fresh Traefik per sandbox, which used to
fail with::

    Container sandbox-ai-dev-factory-…-traefik-1 Starting
    Bind for 0.0.0.0:80 failed: port is already allocated

Traefik now lives in its own infra compose file
(``deploy/infra/docker-compose.traefik.yml``) and is started once per
host via ``deploy/infra/start_traefik.sh``.
"""
from __future__ import annotations

import os
import re
import stat
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ROOT_COMPOSE = _REPO_ROOT / "docker-compose.yml"
_INFRA_DIR = _REPO_ROOT / "deploy" / "infra"
_INFRA_COMPOSE = _INFRA_DIR / "docker-compose.traefik.yml"
_INFRA_SCRIPT = _INFRA_DIR / "start_traefik.sh"


def _parse_compose_services(path: Path) -> dict[str, dict]:
    """Tiny YAML-ish parser that extracts service names + image lines.

    We avoid pulling in PyYAML as a test dep — and a fully spec'd parser
    isn't required to assert "service X is/isn't here". We just look for
    the top-level ``services:`` block and the keys directly under it.
    """
    text = path.read_text(encoding="utf-8")
    services: dict[str, dict] = {}
    in_services = False
    current: str | None = None
    for raw in text.splitlines():
        # Strip comments to avoid matching `# traefik:` inside docstrings.
        line_no_comment = raw.split("#", 1)[0].rstrip()
        if not line_no_comment.strip():
            continue
        # Top-level ``services:`` key.
        if re.match(r"^services\s*:\s*$", line_no_comment):
            in_services = True
            current = None
            continue
        if not in_services:
            continue
        # New top-level section → leave services.
        if re.match(r"^\S", line_no_comment):
            in_services = False
            current = None
            continue
        # A direct child of services: exactly 2-space indent + key:
        m = re.match(r"^  ([A-Za-z0-9_-]+)\s*:\s*$", line_no_comment)
        if m:
            current = m.group(1)
            services[current] = {}
            continue
        if current is not None:
            sub = re.match(r"^    ([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$", line_no_comment)
            if sub:
                services[current][sub.group(1)] = sub.group(2)
    return services


# ── Root compose: NO traefik ──────────────────────────────────────────────────


def test_root_compose_does_not_define_traefik():
    services = _parse_compose_services(_ROOT_COMPOSE)
    assert "traefik" not in services, (
        "docker-compose.yml must not contain a 'traefik' service — "
        "sandbox compose runs would spawn it per sandbox and conflict "
        "on port 80. Move it to deploy/infra/docker-compose.traefik.yml."
    )


def test_root_compose_keeps_application_services():
    """Sanity: removing Traefik must not have stripped the app stack."""
    services = _parse_compose_services(_ROOT_COMPOSE)
    assert "api" in services, "api service missing from root compose"
    assert "web" in services, "web service missing from root compose"


def test_root_compose_does_not_bind_port_80():
    """Belt-and-suspenders: even if a future service is named differently,
    no service in the root file should claim port 80 — that belongs to
    the global Traefik exclusively."""
    text = _ROOT_COMPOSE.read_text(encoding="utf-8")
    # Match ``"80:80"`` or ``80:80`` in ports lists, ignoring quoting/spacing.
    forbidden = re.findall(r'^[^#\n]*-\s*"?80:\d+"?\s*$', text, flags=re.MULTILINE)
    assert not forbidden, (
        f"root compose binds port 80 at: {forbidden!r}. "
        "Port 80 belongs to the global Traefik infra compose file."
    )


# ── Infra compose: exactly traefik ────────────────────────────────────────────


def test_infra_compose_file_exists():
    assert _INFRA_COMPOSE.exists(), (
        f"global Traefik compose file is missing: {_INFRA_COMPOSE}"
    )


def test_infra_compose_defines_traefik():
    services = _parse_compose_services(_INFRA_COMPOSE)
    assert "traefik" in services, (
        "deploy/infra/docker-compose.traefik.yml must define the "
        "'traefik' service"
    )


def test_infra_compose_only_defines_infra_services():
    """The infra file should not accidentally take ownership of api/web
    — those belong to the application stack."""
    services = _parse_compose_services(_INFRA_COMPOSE)
    for app_only in ("api", "web"):
        assert app_only not in services, (
            f"deploy/infra/docker-compose.traefik.yml must not declare "
            f"{app_only!r} — that's an application service"
        )


def test_infra_compose_traefik_binds_port_80():
    text = _INFRA_COMPOSE.read_text(encoding="utf-8")
    assert re.search(r'"?80:80"?', text), (
        "global Traefik must publish port 80"
    )


# ── Startup script ────────────────────────────────────────────────────────────


def test_start_traefik_script_exists_and_is_executable():
    assert _INFRA_SCRIPT.exists(), (
        f"deploy/infra/start_traefik.sh missing — required by "
        f"deploy/README.md as the canonical Traefik startup command"
    )
    mode = _INFRA_SCRIPT.stat().st_mode
    assert mode & stat.S_IXUSR, (
        f"{_INFRA_SCRIPT.name} must be chmod +x so users can run "
        f"'bash deploy/infra/start_traefik.sh' from the README"
    )


def test_start_traefik_script_uses_dedicated_project_name():
    """The script MUST use a project name other than the default — that
    keeps Traefik in its own compose project so sandbox ``docker compose
    down`` runs never accidentally tear down the global proxy."""
    text = _INFRA_SCRIPT.read_text(encoding="utf-8")
    assert "-p" in text, (
        f"{_INFRA_SCRIPT.name} must pass '-p <name>' to docker compose"
    )
    assert "ai-dev-factory-infra" in text, (
        "the global Traefik should run under the 'ai-dev-factory-infra' "
        "compose project so it's clearly distinct from app and sandbox runs"
    )


def test_start_traefik_script_references_infra_compose_file():
    text = _INFRA_SCRIPT.read_text(encoding="utf-8")
    assert "docker-compose.traefik.yml" in text, (
        f"{_INFRA_SCRIPT.name} must -f the infra compose file"
    )


# ── Documentation ─────────────────────────────────────────────────────────────


def test_deploy_readme_documents_global_traefik_startup():
    readme = (_REPO_ROOT / "deploy" / "README.md").read_text(encoding="utf-8")
    assert "deploy/infra/start_traefik.sh" in readme, (
        "deploy/README.md must document the global Traefik startup command"
    )
    assert "global" in readme.lower() and "traefik" in readme.lower(), (
        "deploy/README.md must call out that Traefik is global/shared "
        "infrastructure (and not a per-sandbox container)"
    )
