"""Atomic Traefik dynamic route file I/O.

Traefik's file provider watches ``/routes`` with inotify. Partial writes,
direct unlinks, and temp files in the watched directory cause::

    error reading configuration file: ... no such file or directory

This module centralises stable filenames, atomic replace, and safe removal.
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger("control-api")

# Valid empty config — written before delete so Traefik drops routers while
# the inode path still exists (reduces watcher read races).
_EMPTY_ROUTE_YAML = "http:\n  routers: {}\n  services: {}\n"


def route_file_path(routes_dir: Path, sandbox_id: str) -> Path:
    """Stable per-environment route filename: ``{sandbox_id}.yml``."""
    return routes_dir / f"{sandbox_id}.yml"


def atomic_write_route_file(path: Path, content: str) -> None:
    """Write *content* via temp file + fsync + atomic replace."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.parent / f".{path.name}.{os.getpid()}.tmp"
    try:
        fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            data = content.encode("utf-8")
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp_path, path)
        dir_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


def validate_route_file(path: Path) -> str | None:
    """Return an error message if *path* is not a usable route file."""
    if not path.exists():
        return f"route file does not exist: {path}"
    try:
        if path.stat().st_size == 0:
            return f"route file is empty: {path}"
    except OSError as exc:
        return f"cannot stat route file {path}: {exc}"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return f"cannot read route file {path}: {exc}"
    if "http:" not in text or "routers:" not in text:
        return f"route file missing required Traefik keys: {path}"
    return None


def verify_route_visible_in_traefik_container(
    host_route_path: Path,
    *,
    traefik_container_id: str | None = None,
) -> str | None:
    """Check the route file is visible inside Traefik at ``/routes/...``.

    Returns None on success, or an error string. Skips quietly when Docker
    or the infra container is unavailable (dev/test hosts).
    """
    if traefik_container_id is None:
        from .traefik_manager import TraefikManager

        traefik_container_id = TraefikManager().infra_container_id()
    if not traefik_container_id:
        return None
    container_path = f"/routes/{host_route_path.name}"
    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                traefik_container_id,
                "test",
                "-f",
                container_path,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return (
            f"route file missing inside Traefik container at {container_path} "
            f"(host path {host_route_path})"
        )
    return None


def safe_remove_route_file(path: Path) -> None:
    """Remove a route file without leaving Traefik watching a vanished path.

    Replaces content with an empty valid config, then unlinks. No-op if
    the file is already absent.
    """
    path = path.resolve()
    if not path.exists():
        return
    try:
        atomic_write_route_file(path, _EMPTY_ROUTE_YAML)
    except OSError as exc:
        logger.warning("proxy: tombstone write before remove failed %s: %s", path, exc)
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def cleanup_orphan_temp_files(routes_dir: Path) -> None:
    """Remove stale ``.*.tmp`` files left by interrupted writes."""
    for tmp in routes_dir.glob(".*.tmp"):
        try:
            tmp.unlink()
        except OSError:
            pass
