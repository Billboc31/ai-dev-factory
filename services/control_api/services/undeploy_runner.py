"""Generic undeploy and cleanup lifecycle for sandbox runtimes.

Executes project-defined undeploy steps (from deploy.yml) in reverse order,
falls back to a generic docker compose down when no undeploy section is present,
and removes stale pid/lock files during cleanup.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from ..models.schemas import DeployComponent, DeployProfile

logger = logging.getLogger("control-api")

_STEP_TIMEOUT = 120


def _run_step(
    component: DeployComponent,
    compose_project: str,
    env_file: str,
    project_root: Path,
    sandbox_id: str,
) -> None:
    """Execute a single undeploy step; logs warnings on failure but does not raise."""
    if component.type == "docker":
        cmd = (
            f"docker compose -p {compose_project} --env-file {env_file}"
            f" down --remove-orphans"
        )
    else:
        cmd = component.command
        if not cmd:
            logger.warning(
                "undeploy: step %r has no command, skipping (sandbox=%s)",
                component.name, sandbox_id,
            )
            return

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=str(project_root),
            stdin=subprocess.DEVNULL,
            timeout=_STEP_TIMEOUT,
        )
        if result.returncode != 0:
            logger.warning(
                "undeploy: step %r exited %d (sandbox=%s): %s",
                component.name, result.returncode, sandbox_id,
                result.stderr.strip()[:200],
            )
    except subprocess.TimeoutExpired:
        logger.warning(
            "undeploy: step %r timed out after %ds (sandbox=%s)",
            component.name, _STEP_TIMEOUT, sandbox_id,
        )
    except OSError as exc:
        logger.warning(
            "undeploy: step %r failed to launch (sandbox=%s): %s",
            component.name, sandbox_id, exc,
        )


def run_undeploy(
    profile: DeployProfile | None,
    compose_project: str,
    env_file: str,
    project_root: Path,
    sandbox_id: str,
) -> None:
    """Execute undeploy steps in reverse order, or fall back to docker compose down.

    Idempotent: step failures are logged but do not abort remaining steps.
    """
    if profile is None or not profile.undeploy:
        cmd = (
            f"docker compose -p {compose_project} --env-file {env_file}"
            f" down --remove-orphans"
        )
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                cwd=str(project_root),
                stdin=subprocess.DEVNULL,
                timeout=_STEP_TIMEOUT,
            )
            if result.returncode != 0:
                logger.warning(
                    "undeploy: fallback compose down exited %d (sandbox=%s): %s",
                    result.returncode, sandbox_id, result.stderr.strip()[:200],
                )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning(
                "undeploy: fallback compose down failed (sandbox=%s): %s",
                sandbox_id, exc,
            )
        return

    for component in reversed(profile.undeploy):
        _run_step(component, compose_project, env_file, project_root, sandbox_id)


def run_cleanup(
    profile: DeployProfile | None,
    sandbox_dir: Path,
    runtime_root: Path | None,
    sandbox_id: str,
) -> None:
    """Execute cleanup hooks from the profile, then remove stale pid/lock files.

    Idempotent: hook failures are logged but do not abort remaining cleanup.
    """
    if profile and profile.cleanup:
        for step in profile.cleanup:
            if step.type != "host" or not step.command:
                continue
            try:
                result = subprocess.run(
                    step.command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    cwd=str(sandbox_dir),
                    stdin=subprocess.DEVNULL,
                    timeout=_STEP_TIMEOUT,
                )
                if result.returncode != 0:
                    logger.warning(
                        "cleanup: step %r exited %d (sandbox=%s)",
                        step.name, result.returncode, sandbox_id,
                    )
            except (subprocess.TimeoutExpired, OSError) as exc:
                logger.warning(
                    "cleanup: step %r failed (sandbox=%s): %s",
                    step.name, sandbox_id, exc,
                )

    roots = [r for r in (runtime_root, sandbox_dir) if r is not None]
    for root in roots:
        if not root.exists():
            continue
        for pattern in ("*.pid", "*.lock"):
            for stale in root.glob(pattern):
                try:
                    stale.unlink()
                    logger.debug(
                        "cleanup: removed stale file %s (sandbox=%s)", stale, sandbox_id,
                    )
                except OSError:
                    pass
