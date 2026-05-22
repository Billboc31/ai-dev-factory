"""Docker Compose project-name helpers.

Compose enforces ``^[a-z0-9][a-z0-9_-]*$`` on project names (passed
either via ``-p`` on the CLI or via ``COMPOSE_PROJECT_NAME``). Our
sandbox runner builds names from the project id and a UTC timestamp,
e.g. ``sandbox-ai-dev-factory-20260522T204456`` — which fails because
of the uppercase ``T`` introduced by ``%Y%m%dT%H%M%S``.

This module is the single source of truth for normalising sandbox
compose project names. It is intentionally dependency-free so both
the host-side worker (``tools/agent_runner/run_sandbox.py``) and the
in-container sandbox manager (``services/control_api/services/
sandbox_manager.py``) can import it.
"""
from __future__ import annotations

import hashlib
import re

__all__ = ["normalize_compose_project_name"]


_INVALID_CHARS_RE = re.compile(r"[^a-z0-9_-]")
_REPEATED_SEP_RE = re.compile(r"[-_]{2,}")
_LEADING_NON_ALNUM_RE = re.compile(r"^[^a-z0-9]+")


def normalize_compose_project_name(name: str) -> str:
    """Coerce *name* into a valid Docker Compose project name.

    Rules applied (in order):

    1. casefold to lowercase
    2. replace any character not in ``[a-z0-9_-]`` with ``-``
    3. collapse runs of separators (``-``/``_``) into a single ``-``
    4. strip leading non-alphanumeric characters
    5. strip trailing separators
    6. if the result is empty, fall back to ``s<8-hex-of-original>``
       so the function is total and uniqueness is preserved even for
       degenerate inputs (e.g. ``"!!!"``)

    The function is deterministic: the same input always produces the
    same output, which lets callers safely embed the result in state
    files, env files and CLI arguments without re-normalising.
    """
    if not isinstance(name, str):
        raise TypeError(f"compose project name must be str, got {type(name).__name__}")

    lowered = name.casefold()
    cleaned = _INVALID_CHARS_RE.sub("-", lowered)
    collapsed = _REPEATED_SEP_RE.sub("-", cleaned)
    stripped = _LEADING_NON_ALNUM_RE.sub("", collapsed).rstrip("-_")

    if not stripped:
        digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
        return f"s{digest}"
    return stripped
