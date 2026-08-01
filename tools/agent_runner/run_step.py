#!/usr/bin/env python3
"""Minimal local runner for ai-dev-factory ticket steps."""

from __future__ import annotations

import argparse
import datetime
import os
import re
import shlex
import signal
import subprocess
import sys
from pathlib import Path

# Default wall-clock limit for --exec-cmd agent invocations. Override with
# AGENT_EXEC_TIMEOUT_SECONDS (0 = unlimited). Prevents perpetual hangs when an
# agent waits forever on empty background shell task outputs.
_DEFAULT_EXEC_TIMEOUT_SECONDS = 7200


# Step processes (planner/coder/reviewer/tester) spawn an external agent
# via ``execute_external_command``. Suppress .pyc generation in this process
# and every subprocess so the worktree stays clean between steps.
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
sys.dont_write_bytecode = True


RUN_SUBDIRS = ["prompts", "reviews", "fixes", "tests", "memory"]

STEP_ALIASES = {
    "planner": "planner",
    "plan": "planner",
    "coder": "coder",
    "code": "coder",
    "review": "review",
    "reviewer": "review",
    "tester": "tester",
    "test": "tester",
    "memory-updater": "memory-updater",
    "memory": "memory-updater",
    "memory-apply": "memory-apply",
    "conflict-resolver": "conflict-resolver",
    "conflict": "conflict-resolver",
}

DEFAULT_OUTPUTS = {
    "planner": "plan.md",
    "coder": "implementation-output.md",
    "review": "reviews/review.md",
    "tester": "tests/test-report.md",
    "memory-updater": "memory/memory-update.md",
    "memory-apply": "memory/memory-apply.md",
    "conflict-resolver": "conflict/resolution.md",
}

WORKFLOW_SEQUENCE = [
    ("PLAN_APPROVED", "coder"),
    ("IMPLEMENTATION_APPROVED", "memory-updater"),
    ("MEMORY_APPROVED", "done"),
]

GLOBAL_CONTEXT_FILE = "docs/ai/global-context.md"

STEP_ROLE_FILES: dict[str, str] = {
    "planner": "ai/roles/planner.md",
    "coder": "ai/roles/coder.md",
    "review": "ai/roles/reviewer.md",
    "tester": "ai/roles/tester.md",
    "conflict-resolver": "ai/roles/conflict-resolver.md",
}

STEP_SKILL_FILES: dict[str, list[str]] = {
    "planner": ["workflow-discipline", "architecture-discipline", "documentation"],
    "coder": ["workflow-discipline", "git-discipline", "code-quality", "refactor-safety", "security"],
    "review": ["workflow-discipline", "code-quality", "refactor-safety", "security"],
    "tester": ["workflow-discipline", "testing", "debugging"],
    "conflict-resolver": ["workflow-discipline", "git-discipline", "code-quality", "refactor-safety"],
}

_FORBIDDEN_PHRASES = [
    "implémentation terminée",
    "implementation complete",
    "implementation completed",
    "syntaxe valide",
    "syntax clean",
    "all changes are in place",
    "changements appliqués",
    "changes applied",
    "voici ce qui a été fait",
    "résumé des changements",
    "modifications effectuées",
]

# Recognised section headers for planner output. Each group lists synonyms
# in both French and English. The validator accepts a plan if at least one
# synonym from any group is present — we do not require the full schema.
#
# The canonical structure documented in ai/roles/planner.md is:
#   ## Contexte / Context
#   ## Objectif / Objective
#   ## Inclus / Included
#   ## Hors scope / Excluded
#   ## Critères d'acceptation / Acceptance criteria
_REQUIRED_SECTION_GROUPS = {
    "contexte": [
        "## contexte",
        "## context",
        "## diagnostic",
        "## contexte et diagnostic",
        "## contexte technique",
    ],
    "objectif": [
        "## objectif",
        "## objectifs",
        "## but",
        "## objective",
        "## goal",
        "## goals",
    ],
    "inclus": [
        "## inclus",
        "## included",
        "## périmètre",
        "## scope",
        "## changements prévus",
        "## plan",
        "## étapes",
        "## étapes d’implémentation",
        "## steps",
        "## implementation",
        "## implementation steps",
    ],
    "hors scope": [
        "## hors scope",
        "## hors périmètre",
        "## non inclus",
        "## exclusions",
        "## excluded",
        "## out of scope",
        "## not in scope",
    ],
    "critères d’acceptation": [
        "## critères d’acceptation",
        "## critères d'acceptation",
        "## critères",
        "## validation",
        "## critères de validation",
        "## acceptance criteria",
        "## acceptance",
    ],
}

# Validation thresholds — kept low on purpose. We only reject plans that are
# *both* short *and* unstructured. Trivial tickets legitimately produce short
# plans, so a plan with at least one recognised section is always accepted
# regardless of length. Real quality checks are the reviewer's job.
_MIN_PLAN_WORDS = 20

# Curated openings that signal the output is a meta-report *about* the
# artifact instead of the artifact itself. Each pattern is anchored at the
# start of the first prose line (after stripping leading headings). The
# regexes are intentionally narrow to avoid false positives.
# Soft openings: suppressed when the body carries real artifact signals
# (bullets, paths, code fences).
_META_REPORT_OPENING_PATTERNS: tuple[str, ...] = (
    r"^the plan(?:\s+(?:has been|was|now|is)\b|\s+rewritten\b)",
    r"^this plan\b",
    r"^plan rewritten\b",
    r"^key points covered\b",
    r"^the document now\b",
    r"^the artifact (?:was|has been) (?:rewritten|updated|revised)",
)

# Hard openings: always meta-reports — tool-using agents often Write the real
# plan to disk then print one of these summaries to stdout. Bullets/paths in
# the summary must NOT suppress the heuristic.
_HARD_META_REPORT_OPENING_PATTERNS: tuple[str, ...] = (
    r"^plan written to\b",
    r"^the plan (?:is|has been|was) written(?:\s+to\b)?",
    r"^`?runs/t\d+/plan\.md`?\s+(?:is|has been)\s+written",
    r"^`?runs/t\d+/plan\.md`?\s+has been written\b",
)

# Human-readable reason emitted when the meta-report heuristic fires.
# Kept stable so the runner can match on it when deciding whether to retry.
META_REPORT_REASON = "plan looks like a meta-report, not the artifact itself"

_QUOTA_PATTERNS: tuple[str, ...] = (
    "rate limit",
    "ratelimit",
    "quota exceeded",
    "too many requests",
    "usage limit",
    "ratelimiterror",
    r"hit your limit",
    r"hit the limit",
    r"you['']ve hit your limit",
)

_QUOTA_RESET_RE = re.compile(
    r"resets?\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)(?:\s*\(([^)]+)\))?",
    re.IGNORECASE,
)

_WRITE_PERMISSION_PATTERNS: tuple[str, ...] = (
    "write permission",
    "please grant",
    r"grant.{0,20}permission",
    r"need.{0,20}permission",
    "auto-accept edit",
)

_PROVIDER_ERROR_PATTERNS: tuple[str, ...] = (
    "internal server error",
    "service unavailable",
    "bad gateway",
    "overloaded_error",
    "overloaded",
    "apierror",
    "anthropicerror",
    r"\b502\b",
    r"\b503\b",
)


class RunnerError(Exception):
    pass


def validate_ticket_id(ticket_id: str) -> str:
    if not re.fullmatch(r"T\d{3,}", ticket_id):
        raise RunnerError("ticket id must look like T002 or T123")
    return ticket_id


def normalize_step(step: str) -> str:
    normalized = STEP_ALIASES.get(step.strip().lower())
    if not normalized:
        allowed = ", ".join(sorted(STEP_ALIASES))
        raise RunnerError(f"unknown step '{step}'. Allowed values: {allowed}")
    return normalized


def ensure_safe_relative_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        raise RunnerError("output path must be relative to the repository root")
    if ".." in path.parts:
        raise RunnerError("output path must not contain '..'")
    return path


def prompt_candidates(ticket_id: str, step: str) -> list[Path]:
    names = [f"{ticket_id}-{step}.md"]
    if step == "review":
        names.append(f"{ticket_id}-reviewer.md")
    if step == "memory-updater":
        names.append(f"{ticket_id}-memory.md")
    candidates = [Path("prompts") / name for name in names]
    candidates.append(Path("prompts") / "generic" / f"{step}.md")
    return candidates


def find_prompt(ticket_id: str, step: str) -> tuple[Path, str]:
    for candidate in prompt_candidates(ticket_id, step):
        if candidate.exists():
            source = "generic" if candidate.parent.name == "generic" else "ticket-specific"
            _log_runtime(ticket_id, f"prompt: resolved={candidate} source={source}")
            return candidate, source
    attempted = ", ".join(str(p) for p in prompt_candidates(ticket_id, step))
    raise RunnerError(f"prompt not found. Tried: {attempted}")


def ensure_run_tree(ticket_id: str) -> Path:
    run_dir = Path("runs") / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    for subdir in RUN_SUBDIRS:
        (run_dir / subdir).mkdir(parents=True, exist_ok=True)

    status_path = run_dir / "workflow-status.md"
    if not status_path.exists():
        status_path.write_text(
            "# Workflow Status\n\n"
            "## Current Status\n\n"
            "- PLAN_APPROVED\n"
            "- PLAN_FIX_REQUIRED\n"
            "- IMPLEMENTATION_APPROVED\n"
            "- IMPLEMENTATION_FIX_REQUIRED\n"
            "- MEMORY_APPROVED\n"
            "- MEMORY_FIX_REQUIRED\n\n"
            "## Risk Level\n\n"
            "- AUTO_SAFE\n"
            "- CHAT_REVIEW_REQUIRED\n"
            "- HIGH_RISK\n\n"
            "## Notes\n",
            encoding="utf-8",
        )
    return run_dir


def read_next_step(ticket_id: str) -> str:
    status_path = Path("runs") / ticket_id / "workflow-status.md"
    if not status_path.exists():
        return "planner"

    content = status_path.read_text(encoding="utf-8")
    for status, next_step in WORKFLOW_SEQUENCE:
        if status in content:
            return next_step
    return "planner"


def default_output_path(ticket_id: str, step: str) -> Path:
    return Path("runs") / ticket_id / DEFAULT_OUTPUTS[step]


def write_output(output_path: Path, content: str) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def update_status(ticket_id: str, status: str) -> None:
    if not re.fullmatch(r"[A-Z_]+", status):
        raise RunnerError("status must contain only uppercase letters and underscores")

    run_dir = ensure_run_tree(ticket_id)
    status_path = run_dir / "workflow-status.md"
    existing = status_path.read_text(encoding="utf-8") if status_path.exists() else "# Workflow Status\n"
    status_path.write_text(existing.rstrip() + f"\n\n## Last Update\n\n{status}\n", encoding="utf-8")


def resolve_exec_timeout_seconds(explicit: int | None = None) -> int | None:
    """Return timeout in seconds for ``execute_external_command``, or None if unlimited.

    Priority: explicit arg > ``AGENT_EXEC_TIMEOUT_SECONDS`` > default (7200).
    A value ``<= 0`` means unlimited.
    """
    if explicit is not None:
        return None if explicit <= 0 else explicit
    raw = os.environ.get("AGENT_EXEC_TIMEOUT_SECONDS")
    if raw is not None and raw.strip() != "":
        try:
            value = int(raw)
        except ValueError as exc:
            raise RunnerError(
                f"AGENT_EXEC_TIMEOUT_SECONDS must be an integer, got {raw!r}"
            ) from exc
        return None if value <= 0 else value
    return _DEFAULT_EXEC_TIMEOUT_SECONDS


def execute_external_command(
    command_text: str,
    prompt_content: str,
    timeout: int | None = None,
) -> tuple[str, str, int]:
    command = shlex.split(command_text)
    if not command:
        raise RunnerError("external command must not be empty")

    # Force ``PYTHONDONTWRITEBYTECODE=1`` in the environment of the spawned
    # planner/coder/reviewer/tester so they cannot leave ``.pyc`` files behind
    # in the worktree. The variable is harmless for non-Python agents
    # (claude, openai, etc.).
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    effective_timeout = resolve_exec_timeout_seconds(timeout)

    # Own process group so a timeout can kill Claude *and* its hung shell
    # waiters (grandchildren), which subprocess.run alone would leave behind.
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
        env=env,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(input=prompt_content, timeout=effective_timeout)
        return stdout, stderr, proc.returncode or 0
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except OSError:
                pass
        stdout, stderr = proc.communicate()
        limit = effective_timeout if effective_timeout is not None else 0
        msg = f"[timeout] external command exceeded {limit}s\n"
        return stdout or "", (stderr or "") + msg, 124


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_runtime(ticket_id: str, message: str) -> None:
    log_path = Path("runs") / ticket_id / "runtime.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{_now_iso()}] {message}\n")


def _next_attempt_number(ticket_id: str, step: str) -> int:
    prompts_dir = Path("runs") / ticket_id / "prompts"
    existing = list(prompts_dir.glob(f"{step}-attempt-*.md"))
    return len(existing) + 1


def _write_prompt_snapshot(ticket_id: str, step: str, prompt: str) -> Path:
    attempt = _next_attempt_number(ticket_id, step)
    prompts_dir = Path("runs") / ticket_id / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = prompts_dir / f"{step}-attempt-{attempt}.md"
    snapshot_path.write_text(prompt, encoding="utf-8")
    _log_runtime(ticket_id, f"snapshot: runtime-prompt={snapshot_path}")
    return snapshot_path


def compose_runtime_prompt(
    ticket_id: str,
    step: str,
    task_content: str,
    project_root: Path | None = None,
) -> str:
    """Compose full runtime prompt: GLOBAL CONTEXT + ROLE + SKILLS + TASK.

    When project_root is provided, context files are resolved preferentially from
    <project_root>/<rel>; if absent there, falls back to Path(rel) (factory-relative CWD).
    """
    sections: list[tuple[str, str]] = []

    def _resolve(rel: str) -> Path:
        if project_root is not None:
            candidate = project_root / rel
            if candidate.exists():
                return candidate
        return Path(rel)

    global_ctx_path = _resolve(GLOBAL_CONTEXT_FILE)
    if global_ctx_path.exists():
        sections.append(("GLOBAL CONTEXT", global_ctx_path.read_text(encoding="utf-8")))
        _log_runtime(ticket_id, f"compose: global-context={global_ctx_path}")
    else:
        _log_runtime(ticket_id, f"compose: global-context not found at {global_ctx_path} — skipped")

    role_file = STEP_ROLE_FILES.get(step)
    if role_file:
        role_path = _resolve(role_file)
        if role_path.exists():
            sections.append(("ROLE", role_path.read_text(encoding="utf-8")))
            _log_runtime(ticket_id, f"compose: role={role_path}")
        else:
            _log_runtime(ticket_id, f"compose: role not found at {role_path} — skipped")

    for skill_name in STEP_SKILL_FILES.get(step, []):
        skill_path = _resolve(f"ai/skills/{skill_name}.md")
        if skill_path.exists():
            sections.append((f"SKILL: {skill_name}", skill_path.read_text(encoding="utf-8")))
            _log_runtime(ticket_id, f"compose: skill={skill_path}")
        else:
            _log_runtime(ticket_id, f"compose: skill not found at {skill_path} — skipped")

    sections.append(("TASK", task_content))
    _log_runtime(ticket_id, "compose: task (canonical prompt)")

    parts = [f"# {label}\n\n{content.strip()}" for label, content in sections]
    return "\n\n---\n\n".join(parts)


def _first_prose_line(content: str) -> str:
    """Return the first non-empty, non-heading line lowercased, or ``\"\"``."""
    for line in content.splitlines():
        line_stripped = line.strip()
        if not line_stripped:
            continue
        if line_stripped.startswith("#"):
            continue
        return line_stripped.lower()
    return ""


def _looks_like_meta_report(content: str) -> bool:
    """High-precision detector for outputs that describe the artifact rather
    than *being* the artifact.

    Returns ``True`` when:

    1. The first prose line matches a **hard** meta-report opening
       (``_HARD_META_REPORT_OPENING_PATTERNS``) — always rejected, even if
       the body has bullets/paths (chatty summaries about ``plan.md``).
    2. Or it matches a **soft** opening (``_META_REPORT_OPENING_PATTERNS``)
       *and* the file contains no fenced code block, no bullet list, and no
       file-path-like token. Those three signals suppress soft matches so a
       real plan that mentions "The plan now ensures X" inside a section
       still passes.
    """
    stripped = content.strip()
    if not stripped:
        return False

    opening = _first_prose_line(stripped)
    if not opening:
        return False

    if any(re.match(pat, opening) for pat in _HARD_META_REPORT_OPENING_PATTERNS):
        return True

    if not any(re.match(pat, opening) for pat in _META_REPORT_OPENING_PATTERNS):
        return False

    if "```" in stripped:
        return False
    for line in stripped.splitlines():
        s = line.lstrip()
        if s.startswith("- ") or s.startswith("* "):
            return False
    if re.search(
        r"\b[\w\-./]+\.(?:py|md|ts|tsx|js|jsx|json|yml|yaml|sh|toml|ini|cfg)\b",
        stripped,
    ):
        return False
    if re.search(
        r"\b(?:runs|tools|tests|prompts|docs|ai|services|apps)/[\w./-]+",
        stripped,
    ):
        return False
    return True


def resolve_exec_output_content(step: str, output_path: Path, stdout: str) -> str:
    """Choose between agent stdout and an on-disk file the agent may have written.

    Tool-using agents (Claude Code) often ``Write`` the real artifact to
    ``output_path`` then print a chatty meta-summary to stdout. Blindly
    overwriting with stdout destroys the valid artifact. Prefer the on-disk
    file when it already validates as a plan and stdout does not.
    """
    if step != "planner":
        return stdout
    if not output_path.is_file():
        return stdout
    try:
        disk = output_path.read_text(encoding="utf-8")
    except OSError:
        return stdout
    if not disk.strip():
        return stdout

    disk_reasons = validate_planner_output(disk, artifact_type="plan")
    if disk_reasons:
        return stdout

    stdout_reasons = validate_planner_output(stdout, artifact_type="plan")
    if stdout_reasons or disk.strip() != stdout.strip():
        return disk
    return stdout


def validate_planner_output(content: str, artifact_type: str = "plan") -> list[str]:
    """Return rejection reasons; empty list means the output is valid.

    Validation is intentionally permissive and decoupled from a fixed word
    count or exact wording:

    - **Structural check** — accept the plan if at least one recognised
      section header (FR or EN, synonyms in ``_REQUIRED_SECTION_GROUPS``) is
      present. A plan with sections is accepted *regardless of length* so
      trivial tickets can produce short legitimate plans.
    - **Fallback short-circuit** — only when *no* section header is found do
      we apply a minimum-length sanity check (``_MIN_PLAN_WORDS``). This
      catches empty or one-line garbage output while still allowing
      free-form plans of substantial length to pass with a structural
      complaint.
    - **Forbidden phrases** — reviewer/coder telltales remain rejected
      regardless of structure.
    - **Meta-report heuristic** (``artifact_type == "plan"``) — reject
      outputs that read like a status report about the artifact rather than
      the artifact itself (e.g. start with "The plan has been rewritten…").

    Deeper quality checks (sound design, complete coverage) are the
    reviewer's job — not this gate.

    ``artifact_type`` is the expected output kind (one of ``plan``,
    ``review``, ``fix``, ``code``, ``ADR``). Only ``plan`` is wired today;
    the parameter exists so future tickets can add type-aware soft
    heuristics without churn at every call site.
    """
    reasons: list[str] = []
    stripped = content.strip()
    lower = stripped.lower()

    code_stripped = re.sub(r"```[\s\S]*?```", "", lower)
    code_stripped = re.sub(r"`[^`\n]+`", "", code_stripped)

    has_section = any(
        synonym in lower
        for synonyms in _REQUIRED_SECTION_GROUPS.values()
        for synonym in synonyms
    )

    if not has_section:
        word_count = len(stripped.split())
        if word_count < _MIN_PLAN_WORDS:
            reasons.append(
                f"plan trop court ({word_count} mots) et sans section reconnue"
            )
        else:
            reasons.append(
                "plan sans section reconnue (Objective/Included/Excluded/"
                "Acceptance criteria — ou équivalents FR)"
            )

    for phrase in _FORBIDDEN_PHRASES:
        if phrase in code_stripped:
            reasons.append(f"phrase interdite: «{phrase}»")

    if artifact_type == "plan" and _looks_like_meta_report(content):
        reasons.append(META_REPORT_REASON)

    return reasons


def parse_quota_reset_at(text: str) -> str | None:
    """Return ISO-UTC reset time parsed from provider messages like 'resets 9:40pm (Europe/Paris)'."""
    match = _QUOTA_RESET_RE.search(text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    ampm = match.group(3).lower()
    tz_name = (match.group(4) or "UTC").strip()

    if ampm == "pm" and hour != 12:
        hour += 12
    elif ampm == "am" and hour == 12:
        hour = 0

    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(tz_name)
    except Exception:
        tz = datetime.timezone.utc

    now_local = datetime.datetime.now(tz)
    candidate = now_local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now_local:
        candidate += datetime.timedelta(days=1)

    return candidate.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _quota_message_line(text: str) -> str | None:
    for line in text.splitlines():
        lower = line.lower()
        for pattern in _QUOTA_PATTERNS:
            if re.search(pattern, lower):
                cleaned = line.strip()
                return cleaned[:500] if cleaned else None
    return None


def extract_quota_alert_info(text: str) -> dict[str, str] | None:
    """Return quota alert metadata when *text* indicates a provider quota/limit."""
    if classify_runtime_failure(1, text, "") != "quota_exceeded":
        return None

    message = _quota_message_line(text)
    reset_at = parse_quota_reset_at(text)
    info: dict[str, str] = {}
    if message:
        info["message"] = message
    if reset_at:
        info["reset_at"] = reset_at
    return info or {"message": "Provider quota limit reached"}


def classify_runtime_failure(return_code: int, stdout: str, stderr: str) -> str:
    """Return the most likely failure category for a step execution.

    Categories in priority order:
      process_crashed, process_timeout, quota_exceeded, write_permission_missing,
      provider_error, empty_output, process_failed, unknown
    """
    combined = (stdout + "\n" + stderr).lower()

    if return_code < 0:
        return "process_crashed"

    if return_code == 124 or "[timeout]" in combined:
        return "process_timeout"

    for pattern in _QUOTA_PATTERNS:
        if re.search(pattern, combined):
            return "quota_exceeded"

    for pattern in _WRITE_PERMISSION_PATTERNS:
        if re.search(pattern, combined):
            return "write_permission_missing"

    for pattern in _PROVIDER_ERROR_PATTERNS:
        if re.search(pattern, combined):
            return "provider_error"

    if not stdout.strip():
        return "empty_output"

    if return_code != 0:
        return "process_failed"

    return "unknown"


def show_next(ticket_id: str) -> None:
    step = read_next_step(ticket_id)
    if step == "done":
        print("Workflow complete.")
        return

    prompt_path, _ = find_prompt(ticket_id, step)
    output_path = default_output_path(ticket_id, step)
    print(f"Next step: {step}")
    print(f"Prompt: {prompt_path}")
    print(f"Expected output: {output_path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one ai-dev-factory ticket step locally.")
    parser.add_argument("ticket_id", help="Ticket id, for example T002")
    parser.add_argument("step", nargs="?", help="Step, for example planner, coder, review")
    parser.add_argument("--show-prompt", action="store_true", help="Print the runtime prompt to stdout")
    parser.add_argument("--next", action="store_true", help="Show the next workflow step")
    parser.add_argument("--exec-cmd", help="Run an explicit external command, passing the prompt on stdin")
    parser.add_argument(
        "--exec-timeout",
        type=int,
        default=None,
        help=(
            "Wall-clock timeout in seconds for --exec-cmd "
            "(default: AGENT_EXEC_TIMEOUT_SECONDS or 7200; 0 = unlimited)"
        ),
    )
    parser.add_argument("--output-path", help="Override output path when using --exec-cmd (relative to repo root)")
    parser.add_argument("--stderr-log", help="Relative path where stderr should be written")
    parser.add_argument(
        "--write-output",
        nargs="?",
        const="__DEFAULT__",
        help="Write stdin to an artifact path. If no path is provided, use the default for the step.",
    )
    parser.add_argument("--set-status", help="Append a workflow status to runs/TXXX/workflow-status.md")
    parser.add_argument(
        "--extra-context-file",
        help="Relative path to a file appended to the runtime prompt when using --show-prompt or --exec-cmd",
    )
    parser.add_argument(
        "--project-root",
        help="Absolute path to a managed project root; context files (ai/, docs/) are resolved from there first",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    try:
        ticket_id = validate_ticket_id(args.ticket_id)
        ensure_run_tree(ticket_id)

        if args.next:
            show_next(ticket_id)
            return 0

        if not args.step:
            raise RunnerError("a step is required unless using --next")

        step = normalize_step(args.step)
        prompt_path, prompt_source = find_prompt(ticket_id, step)
        prompt_content = prompt_path.read_text(encoding="utf-8")

        if prompt_source == "generic":
            ticket_md_path = Path("runs") / ticket_id / "ticket.md"
            if not ticket_md_path.exists():
                raise RunnerError(
                    f"generic prompt requires runs/{ticket_id}/ticket.md — file not found"
                )
            ticket_content = ticket_md_path.read_text(encoding="utf-8")
            prompt_content = prompt_content + "\n\n" + ticket_content
            _log_runtime(ticket_id, f"prompt: generic fallback — injecting {ticket_md_path}")

        extra_content = None
        if args.extra_context_file:
            extra_path = ensure_safe_relative_path(args.extra_context_file)
            if not extra_path.exists():
                raise RunnerError(f"extra-context-file not found: {extra_path}")
            extra_content = extra_path.read_text(encoding="utf-8")

        project_root = Path(args.project_root).resolve() if args.project_root else None
        effective_prompt = compose_runtime_prompt(ticket_id, step, prompt_content, project_root=project_root)
        if extra_content:
            effective_prompt = (
                effective_prompt
                + "\n\n---\n\n## Contexte de retry injecté par run_ticket.py\n\n"
                + extra_content
            )
            _log_runtime(ticket_id, f"compose: extra-context={args.extra_context_file}")

        if args.show_prompt:
            _log_runtime(ticket_id, "compose: show-prompt runtime rendering")
            print(effective_prompt)

        if args.exec_cmd:
            _write_prompt_snapshot(ticket_id, step, effective_prompt)
            stdout, stderr, return_code = execute_external_command(
                args.exec_cmd,
                effective_prompt,
                timeout=args.exec_timeout,
            )

            failure_class = classify_runtime_failure(return_code, stdout, stderr)
            if return_code != 0:
                _log_runtime(ticket_id, f"runtime failure: {failure_class} (rc={return_code})")
            elif failure_class in ("write_permission_missing", "empty_output"):
                _log_runtime(ticket_id, f"runtime warning: {failure_class} (rc=0, non-blocking)")

            if args.output_path:
                output_path = ensure_safe_relative_path(args.output_path)
            else:
                output_path = default_output_path(ticket_id, step)

            content = resolve_exec_output_content(step, output_path, stdout)
            if content is not stdout:
                _log_runtime(
                    ticket_id,
                    f"compose: preferring on-disk {output_path} over chatty stdout "
                    f"(agent Write beat meta-report)",
                )
            write_output(output_path, content)

            if args.stderr_log:
                stderr_path = ensure_safe_relative_path(args.stderr_log)
                write_output(stderr_path, stderr)

            print(f"command exit code: {return_code}")
            print(f"stdout written to: {output_path}")

            if args.stderr_log:
                print(f"stderr written to: {args.stderr_log}")

            return return_code

        if args.write_output is not None:
            if args.write_output == "__DEFAULT__":
                output_path = default_output_path(ticket_id, step)
            else:
                output_path = ensure_safe_relative_path(args.write_output)

            content = sys.stdin.read()
            write_output(output_path, content)
            print(f"wrote {output_path}")

        if args.set_status:
            update_status(ticket_id, args.set_status)
            print(f"updated runs/{ticket_id}/workflow-status.md")

        if not args.show_prompt and args.write_output is None and not args.set_status and not args.exec_cmd:
            print(f"prompt: {prompt_path}")
            print(f"run dir: runs/{ticket_id}")
            print("Use --show-prompt, --write-output, --exec-cmd or --next to perform an action.")

    except RunnerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))