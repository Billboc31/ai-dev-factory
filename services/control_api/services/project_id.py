"""Project ID normalization, validation, and path-containment helpers."""

from __future__ import annotations

import re
from pathlib import Path

_VALID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,62}[a-z0-9]$|^[a-z0-9]$")
_COLLAPSE_RE = re.compile(r"[^a-z0-9_-]+")
_MAX_LEN = 64


def normalize_project_id(raw: str) -> str:
    """Derive a valid project_id from an arbitrary name or path.

    Lowercases, collapses unsupported characters to ``-``, trims leading/trailing
    dashes, and truncates to ``_MAX_LEN``.  Raises ``ValueError`` if the result
    would be empty.
    """
    slug = raw.strip().lower()
    slug = _COLLAPSE_RE.sub("-", slug)
    slug = slug.strip("-")
    slug = slug[:_MAX_LEN]
    if not slug:
        raise ValueError(f"cannot derive a valid project_id from: {raw!r}")
    return slug


def validate_project_id(raw: str) -> str:
    """Strictly validate an explicit user-provided project_id.

    Rejects rather than rewrites.  Raises ``ValueError`` describing the problem.
    """
    if not raw or not raw.strip():
        raise ValueError("project_id must not be empty or whitespace-only")
    if raw != raw.strip():
        raise ValueError("project_id must not have leading or trailing whitespace")
    if "/" in raw or "\\" in raw:
        raise ValueError("project_id must not contain path separators")
    if raw == "." or raw == "..":
        raise ValueError("project_id must not be '.' or '..'")
    if ".." in raw:
        raise ValueError("project_id must not contain '..'")
    if not _VALID_RE.match(raw):
        raise ValueError(
            f"project_id {raw!r} is invalid: use only lowercase letters, digits, "
            "hyphens and underscores (max 64 chars, must start and end with alphanumeric)"
        )
    return raw


def assert_contained(runtime_root: Path, project_id: str) -> Path:
    """Resolve ``{runtime_root}/{project_id}`` and assert it stays inside
    ``{runtime_root}/``.

    Returns the resolved project runtime root on success.
    Raises ``ValueError`` on path traversal, symlink escape, or invalid base.
    """
    if runtime_root is None:
        raise ValueError("runtime_base_root is not configured")
    if str(runtime_root) in ("", "."):
        raise ValueError(f"invalid runtime_base_root: {runtime_root!r}")
    validate_project_id(project_id)
    base = runtime_root.resolve()
    candidate = (base / project_id).resolve()

    if not str(candidate).startswith(str(base) + "/") and candidate != base:
        raise ValueError(
            f"project_id {project_id!r} would escape the workspace directory: {candidate}"
        )
    return candidate
