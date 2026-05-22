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


# ── Safety checks for dangerous shell patterns ────────────────────────────────
#
# Each entry is (regex, message_template). The validator scans every `.sh`
# file body line-by-line and flags any match. Patterns are tuned to the
# real failure modes observed in PR #114-style outputs (broad `pkill -f`,
# system-wide docker prunes, hard-coded user homes).
#
# The `pkill -F <pidfile>` form (uppercase `-F`, reads PIDs from a file)
# is the safe alternative and is NOT flagged.

# Match `rm -rf` whose first non-flag argument starts with a variable
# expansion. The capture group lets us inspect whether the expansion uses
# the bash `:?` "fail-if-unset-or-empty" guard.
_RM_RF_VAR_RE = re.compile(
    r"\brm\s+-rf\b(?:\s+-[A-Za-z]+)*\s+\"?(\$\{?[A-Za-z_][A-Za-z0-9_]*[^\s\"]*)"
)

_PROCESS_KILL_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bpkill\s+(?:-[a-eg-zA-EG-Z0-9]+\s+)*-f\b"),
        "uses `pkill -f` (broad process matching) — prefer the supervisor "
        "HTTP API or `pkill -F <pidfile>` (uppercase F, reads PIDs from a "
        "file). See safety rule B2/B3.",
    ),
    (
        re.compile(r"\bpgrep\s+-f\s+\S*run_daemon\.py\b"),
        "looks for `run_daemon.py` system-wide — this matches every "
        "developer's daemon on the host. Use a project-scoped marker "
        "(absolute project path) or a PID file. See safety rule B3.",
    ),
    (
        re.compile(r"\bkillall\b"),
        "uses `killall` (kills every matching process system-wide) — use "
        "PID files or the supervisor HTTP API instead. See safety rule B3.",
    ),
)

_DESTRUCTIVE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\brm\s+-rf\s+/(?:\s|$|\*)"),
        "`rm -rf /` or `rm -rf /*` — catastrophic. See safety rule B4.",
    ),
    (
        re.compile(r"\brm\s+-rf\s+\"?\$HOME\b"),
        "`rm -rf $HOME` — wipes the user's home directory. See safety "
        "rule B4.",
    ),
    (
        re.compile(r"\brm\s+-rf\s+~/?(?:\s|$)"),
        "`rm -rf ~` — wipes the user's home directory. See safety rule B4.",
    ),
)

_HARDCODED_PATH_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"/Users/[A-Za-z][\w.-]*/"),
        "hard-coded macOS user path (`/Users/<name>/…`) — read it from "
        "`deploy/.env` via $AI_DEV_FACTORY_PROJECT_ROOT / $HOST_PROJECT_ROOT "
        "or compute it from `$(cd \"$(dirname \"${BASH_SOURCE[0]}\")\" …)`. "
        "See safety rule B5.",
    ),
    (
        re.compile(r"/home/[A-Za-z][\w.-]*/"),
        "hard-coded Linux user path (`/home/<name>/…`) — read it from "
        "`deploy/.env` or compute it from `$(cd \"$(dirname …)\")`. "
        "See safety rule B5.",
    ),
)

_DOCKER_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"\bdocker\s+system\s+prune\b"),
        "`docker system prune` wipes images/containers/networks from "
        "*every* stack on the host. See safety rule B6.",
    ),
    (
        re.compile(r"\bdocker\s+(?:container|volume|image|network)\s+prune\b"),
        "broad `docker … prune` — affects resources from other projects. "
        "See safety rule B6.",
    ),
)


def _check_rm_rf_variables(content: str) -> list[str]:
    """Flag ``rm -rf "$VAR"`` unless the expansion uses ``${VAR:?…}``.

    Bash's ``${VAR:?msg}`` parameter expansion aborts the script when
    ``VAR`` is unset or empty, which is the idiomatic guard for any
    ``rm -rf`` whose target comes from a variable.
    """
    errors: list[str] = []
    for m in _RM_RF_VAR_RE.finditer(content):
        target = m.group(1)
        # Strip leading quote that may have been swallowed back by the
        # capture (the regex already consumes the opening `"` outside
        # the group, but be defensive).
        target = target.lstrip('"')
        # ``${VAR:?...}`` and ``${VAR:?msg}`` are both safe.
        if re.match(r"^\$\{[A-Za-z_][A-Za-z0-9_]*:\?", target):
            continue
        errors.append(
            f"unguarded `rm -rf {target}` — wrap the variable as "
            f"`${{VAR:?VAR must be set}}` so an unset/empty variable "
            f"aborts the script instead of deleting from /. "
            f"See safety rule B4."
        )
    return errors


def _check_docker_compose_destructive(content: str) -> list[str]:
    """Flag ``docker compose down -v`` (or ``--volumes``) when no
    ``--project-name``/``-p`` scoping flag is present on the same line.

    Tearing down volumes without an explicit project scope can delete
    volumes from any compose stack sharing the default project name.
    """
    errors: list[str] = []
    for line in content.splitlines():
        if not re.search(r"\bdocker\s+compose\b.*\bdown\b", line):
            continue
        if not re.search(r"\s(?:-v|--volumes)\b", line):
            continue
        if re.search(r"\s(?:-p|--project-name)\s+\S+", line):
            continue
        errors.append(
            "`docker compose down -v` without `-p <name>`/"
            "`--project-name <name>` — may destroy volumes from other "
            "stacks. Scope it explicitly. See safety rule B6."
        )
    return errors


# Strip bash line comments before running the safety lint so that a
# script can legitimately *document* what NOT to do without tripping
# the rules. A `#` introduces a comment only when it appears at the
# start of a line or right after whitespace — `${VAR#prefix}` parameter
# expansion is preserved by anchoring the strip to `(^|\s)#`.
_COMMENT_RE = re.compile(r"(?m)(^|\s)#.*$")


def _strip_comments(content: str) -> str:
    return _COMMENT_RE.sub(r"\1", content)


def _check_dangerous_patterns(path: str, content: str) -> list[str]:
    """Run every category of safety check on a single `.sh` file body.

    All matches are reported — the validator does not silently allow a
    broad ``pkill -f`` even when a safer ``pkill -F <pidfile>`` form
    also appears, because the broad line would still execute and kill
    unrelated processes when the pidfile is missing or empty.

    Comments are stripped before scanning so that operational scripts
    can document anti-patterns ("# never use: pkill -f run_daemon.py")
    without failing validation.
    """
    errors: list[str] = []
    scan = _strip_comments(content)

    for pattern, message in (
        _PROCESS_KILL_PATTERNS
        + _DESTRUCTIVE_PATTERNS
        + _HARDCODED_PATH_PATTERNS
        + _DOCKER_PATTERNS
    ):
        if pattern.search(scan):
            errors.append(f"{path}: {message}")

    errors.extend(f"{path}: {e}" for e in _check_rm_rf_variables(scan))
    errors.extend(f"{path}: {e}" for e in _check_docker_compose_destructive(scan))

    return errors


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

    # Run the safety lint on every shell script. Catches operationally
    # dangerous patterns (broad killers, hard-coded user homes, …)
    # whether or not the structural checks above passed.
    errors.extend(_check_dangerous_patterns(path, content))

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
