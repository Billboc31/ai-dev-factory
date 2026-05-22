"""Post-generation validator for AI-produced operational scripts.

Runs **after** the LLM output has been parsed into ``{path: content}``
pairs and **before** anything touches the filesystem or git. Returns a
list of human-readable error strings; an empty list means "ok to write".

The rules pin down the failure modes observed in PR #114:

  * shell scripts wrapped in markdown code fences (```bash … ```);
  * scripts replaced by a one-sentence English description (e.g.
    ``Starts supervisor → Docker stack → daemon …``);
  * ``deployment.md`` truncated to a one-line summary
    (``Updated — covers project overview, …``);
  * required FILE blocks missing entirely.

The function is intentionally pure: no logging, no I/O. The caller
(``run_scripts.main``) is responsible for emitting log lines and
short-circuiting the workflow on failure.
"""
from __future__ import annotations

import re
from collections.abc import Iterable

# Required files the LLM must always produce. Kept here so the validator
# is self-contained — ``run_scripts.py`` continues to own ``_REQUIRED_SCRIPTS``
# as the canonical list and re-exposes it via this module's ``REQUIRED_FILES``
# constant.
REQUIRED_FILES: tuple[str, ...] = (
    ".ai-dev-factory/scripts/bootstrap.sh",
    ".ai-dev-factory/scripts/build.sh",
    ".ai-dev-factory/scripts/start.sh",
    ".ai-dev-factory/scripts/stop.sh",
    ".ai-dev-factory/scripts/restart.sh",
    ".ai-dev-factory/scripts/healthcheck.sh",
    ".ai-dev-factory/deployment.md",
)

# Heuristic: minimum acceptable size of a shell script body (excluding the
# leading shebang line). Anything smaller than this is almost certainly a
# placeholder or a natural-language one-liner. Calibrated from PR #114's
# bad outputs (``start.sh`` was 95 bytes of English prose).
_MIN_SHELL_BODY_BYTES = 40

# Minimum size for deployment.md content. Past failure mode produced a
# 130-byte one-liner; a real deployment guide is several kilobytes.
_MIN_DEPLOYMENT_MD_BYTES = 300

# Substrings whose presence inside a `.sh` file body is always a bug.
# Plain backticks (``) appear legitimately in `$(command)` substitutions
# and in echo/heredoc contexts, so we only match the *fence* form — three
# or more backticks in a row.
_MARKDOWN_FENCE_RE = re.compile(r"```")

# Tokens that suggest the body is actually a Bash script. Used as a
# negative signal: a `.sh` file with NONE of these is almost certainly
# prose. Listing common ones keeps the heuristic robust without being
# language-aware.
_SHELL_TOKENS = (
    "#!/usr/bin/env bash", "#!/bin/bash", "#!/bin/sh",
    "set -e", "set -u", "set -o", "set -euo",
    "if [", "if [[", "fi\n", "done\n",
    "for ", "while ", "case ", "esac",
    "function ", "export ", "source ",
    "cd ", "echo ", "exec ", "exit ",
    "docker ", "git ", "curl ", "wget ",
    "$(", "${", "&&", "||",
)


def _looks_like_shell(body: str) -> bool:
    return any(tok in body for tok in _SHELL_TOKENS)


def _strip_leading_blank_lines(text: str) -> str:
    """Strip leading whitespace/blank lines so the shebang check is robust
    to the LLM emitting a stray newline after ``--- BEGIN FILE ---``."""
    return text.lstrip("\n").lstrip()


def _validate_shell_script(path: str, content: str) -> list[str]:
    """Return a list of error strings for a single `.sh` file."""
    errors: list[str] = []

    if _MARKDOWN_FENCE_RE.search(content):
        errors.append(
            f"{path}: contains a markdown code fence (```), scripts must "
            f"be raw bash"
        )

    stripped = _strip_leading_blank_lines(content)
    if not stripped.startswith(("#!/usr/bin/env bash", "#!/bin/bash", "#!/bin/sh")):
        errors.append(
            f"{path}: missing shebang — first non-blank line must be "
            f"`#!/usr/bin/env bash` (got: {stripped.splitlines()[0][:60]!r})"
        )

    # Body = content minus the first (shebang) line.
    lines = stripped.splitlines()
    body = "\n".join(lines[1:]).strip()
    if len(body.encode("utf-8")) < _MIN_SHELL_BODY_BYTES:
        errors.append(
            f"{path}: body too small ({len(body)} bytes) — looks like a "
            f"placeholder, not an implementation"
        )

    # Inspect only the body (post-shebang) — looking at the whole content
    # would trivially pass when the LLM emits a correct shebang followed by
    # prose, which is exactly PR #114's healthcheck.sh failure.
    if body and not _looks_like_shell(body):
        errors.append(
            f"{path}: body does not look like a shell script (no `set`, "
            f"`if`, `cd`, `echo`, `docker`, … tokens found) — likely a "
            f"natural-language description"
        )

    return errors


def _validate_deployment_md(content: str) -> list[str]:
    errors: list[str] = []
    path = ".ai-dev-factory/deployment.md"

    if len(content.encode("utf-8")) < _MIN_DEPLOYMENT_MD_BYTES:
        errors.append(
            f"{path}: too small ({len(content)} bytes) — must be a real "
            f"deployment guide, not a summary"
        )

    headings = [ln for ln in content.splitlines() if ln.startswith("#")]
    if len(headings) < 2:
        errors.append(
            f"{path}: only {len(headings)} markdown heading(s) — a deployment "
            f"guide needs structured sections (## Overview, ## Scripts, …)"
        )

    return errors


def validate_generated_files(
    files: dict[str, str],
    required: Iterable[str] | None = None,
) -> list[str]:
    """Validate every generated file. Empty list = ok.

    The validator is conservative: it only flags issues that broke real
    runs. A passing run still allows reasonable variability in script
    layout — the goal is to *reject prose and markdown fences*, not to
    enforce a particular coding style.
    """
    errors: list[str] = []
    required_files = tuple(required) if required is not None else REQUIRED_FILES

    # 1. Required files must all be present.
    for rel in required_files:
        if rel not in files:
            errors.append(f"missing required FILE block: {rel}")

    # 2. Per-file content checks.
    for rel, content in files.items():
        if rel.endswith(".sh"):
            errors.extend(_validate_shell_script(rel, content))
        elif rel == ".ai-dev-factory/deployment.md":
            errors.extend(_validate_deployment_md(content))

    return errors
