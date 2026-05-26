"""Architectural tests for the Traefik / sandbox separation.

Traefik must remain a single, **global** instance. Sandbox compose
runs (``docker compose -p sandbox-… up -d`` inside an isolated
worktree) must never spawn their own. Historic failure mode::

    Container sandbox-ai-dev-factory-…-traefik-1 Starting
    Bind for 0.0.0.0:80 failed: port is already allocated

The chosen mechanism is a Docker Compose **profile**: the ``traefik``
service is annotated with ``profiles: [infra]`` so a plain
``docker compose up -d`` (no ``--profile`` flag) brings up only
``api`` + ``web``. The global proxy is started once per host with::

    docker compose --profile infra up -d traefik
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_ROOT_COMPOSE = _REPO_ROOT / "docker-compose.yml"
_DEPLOY_README = _REPO_ROOT / "deploy" / "README.md"


# ── Tiny YAML-ish parser ──────────────────────────────────────────────────────
#
# We avoid pulling PyYAML in as a test dep — for the assertions here
# (does service X exist? does it have a profile? does it bind port 80?)
# a regex-driven walk over the indentation structure is plenty.


def _parse_compose_services(path: Path) -> dict[str, dict]:
    # Block-list-aware fields we care about. Any other ``key:`` with an
    # empty value puts us in a generic "ignore list items" state so we
    # don't accidentally classify e.g. ``volumes:`` items as ports.
    _TRACKED_LISTS = {"profiles", "ports"}

    text = path.read_text(encoding="utf-8")
    services: dict[str, dict] = {}
    in_services = False
    current: str | None = None
    current_list_key: str | None = None  # which list we're appending to

    for raw in text.splitlines():
        line_no_comment = raw.split("#", 1)[0].rstrip()
        if not line_no_comment.strip():
            continue

        if re.match(r"^services\s*:\s*$", line_no_comment):
            in_services = True
            current = None
            current_list_key = None
            continue
        if not in_services:
            continue
        if re.match(r"^\S", line_no_comment):
            in_services = False
            current = None
            current_list_key = None
            continue

        # ``  servicename:`` — direct child of ``services:``.
        m = re.match(r"^  ([A-Za-z0-9_-]+)\s*:\s*$", line_no_comment)
        if m:
            current = m.group(1)
            services[current] = {"profiles": [], "ports": []}
            current_list_key = None
            continue
        if current is None:
            continue

        field = re.match(r"^    ([A-Za-z0-9_-]+)\s*:\s*(.*?)\s*$", line_no_comment)
        if field:
            key, val = field.group(1), field.group(2)
            if val == "" and key in _TRACKED_LISTS:
                current_list_key = key
            else:
                current_list_key = None if val == "" else None  # leave
                # ``- non-block`` field
                if val:
                    services[current][key] = val
            continue

        # ``      - value`` — item of the most recently opened block list.
        list_item = re.match(r"^      -\s*(.+?)\s*$", line_no_comment)
        if list_item and current_list_key is not None:
            value = list_item.group(1).strip('"').strip("'")
            services[current][current_list_key].append(value)
            continue
    return services


# ── Profile gating ────────────────────────────────────────────────────────────


def test_traefik_is_declared_in_root_compose():
    services = _parse_compose_services(_ROOT_COMPOSE)
    assert "traefik" in services, (
        "traefik must remain declared in docker-compose.yml — only its "
        "default-startup visibility changes (gated by a profile)"
    )


def test_traefik_is_gated_behind_infra_profile():
    services = _parse_compose_services(_ROOT_COMPOSE)
    profiles = services["traefik"]["profiles"]
    assert "infra" in profiles, (
        f"traefik must declare 'profiles: [infra]' so it's NOT brought "
        f"up by a plain 'docker compose up -d' — got profiles={profiles!r}"
    )


def test_application_services_are_not_gated():
    """``api`` and ``web`` must start with a plain ``docker compose up`` —
    they're the canonical application stack and must not be gated."""
    services = _parse_compose_services(_ROOT_COMPOSE)
    for app in ("api", "web"):
        assert app in services, f"missing application service: {app}"
        assert services[app]["profiles"] == [], (
            f"{app!r} must NOT be behind a profile (got "
            f"{services[app]['profiles']!r}) — that would break the "
            f"default 'docker compose up -d' workflow"
        )


# ── Port 80 ownership ─────────────────────────────────────────────────────────


def test_only_traefik_binds_port_80():
    services = _parse_compose_services(_ROOT_COMPOSE)
    offenders = [
        name for name, spec in services.items()
        if name != "traefik" and any(p.startswith("80:") for p in spec["ports"])
    ]
    assert not offenders, (
        f"only traefik may bind host port 80; offenders: {offenders}"
    )


def test_traefik_binds_port_80():
    """Sanity: the global proxy still publishes 80."""
    services = _parse_compose_services(_ROOT_COMPOSE)
    assert any(p.startswith("80:") for p in services["traefik"]["ports"]), (
        "traefik must keep its '80:80' port mapping"
    )


# ── Documentation ─────────────────────────────────────────────────────────────


def test_deploy_readme_documents_profile_startup():
    text = _DEPLOY_README.read_text(encoding="utf-8")
    assert "docker compose --profile infra up -d traefik" in text, (
        "deploy/README.md must document the canonical global Traefik "
        "startup command"
    )


def test_deploy_readme_explains_why_traefik_is_gated():
    text = _DEPLOY_README.read_text(encoding="utf-8").lower()
    # The doc should mention BOTH "profile" AND the port-80 failure mode
    # so future readers see the rationale, not just the recipe.
    assert "profile" in text, "deploy/README.md must mention the profile"
    assert "0.0.0.0:80" in text or "port is already allocated" in text, (
        "deploy/README.md must describe the port-80 collision this "
        "gating prevents — otherwise future devs will undo the profile"
    )


# ── docker compose config cross-check (when Docker is available) ──────────────


def test_compose_config_omits_traefik_by_default():
    """Cross-check with Docker Compose's own parser to guarantee that
    our YAML annotation is actually picked up. Skipped if the Docker
    CLI is not installed (e.g. minimal CI runners)."""
    import shutil
    import subprocess

    if shutil.which("docker") is None:
        import pytest
        pytest.skip("docker not available")

    result = subprocess.run(
        ["docker", "compose", "-f", str(_ROOT_COMPOSE), "config", "--services"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        import pytest
        pytest.skip(f"docker compose unavailable: {result.stderr.strip()[:200]}")

    listed = sorted(s for s in result.stdout.splitlines() if s.strip())
    assert "traefik" not in listed, (
        f"`docker compose config --services` returned {listed!r}; "
        f"traefik must NOT appear without --profile infra"
    )
    assert {"api", "web"}.issubset(listed), (
        f"`docker compose config --services` returned {listed!r}; "
        f"api+web must appear by default"
    )


def test_compose_config_includes_traefik_with_infra_profile():
    """Symmetric cross-check: ``--profile infra`` brings traefik back."""
    import shutil
    import subprocess

    if shutil.which("docker") is None:
        import pytest
        pytest.skip("docker not available")

    result = subprocess.run(
        ["docker", "compose", "-f", str(_ROOT_COMPOSE),
         "--profile", "infra", "config", "--services"],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    if result.returncode != 0:
        import pytest
        pytest.skip(f"docker compose unavailable: {result.stderr.strip()[:200]}")

    listed = sorted(s for s in result.stdout.splitlines() if s.strip())
    assert "traefik" in listed, (
        f"`docker compose --profile infra config --services` returned "
        f"{listed!r}; traefik must appear when the infra profile is on"
    )
