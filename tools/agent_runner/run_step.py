#!/usr/bin/env python3
"""Minimal local runner for ai-dev-factory ticket steps.

This script does not call any LLM and does not modify canonical prompts.
It only:
- resolves a canonical prompt for a ticket/step
- creates the standard runs/TXXX folders
- shows the prompt when requested
- writes stdin to a target artifact when requested
- exposes a minimal workflow state machine
- optionally sends a prompt to an explicit external command
"""

from __future__ import annotations

import argparse
import datetime
import re
import shlex
import subprocess
import sys
from pathlib import Path


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
}
DEFAULT_OUTPUTS = {
    "planner": "plan.md",
    "coder": "implementation-output.md",
    "review": "reviews/review.md",
    "tester": "tests/test-report.md",
    "memory-updater": "memory/memory-update.md",
    "memory-apply": "memory/memory-apply.md",
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
}

STEP_SKILL_FILES: dict[str, list[str]] = {
    "planner": ["workflow-discipline", "architecture-discipline", "documentation"],
    "coder": ["workflow-discipline", "git-discipline", "code-quality", "refactor-safety", "security"],
    "review": ["workflow-discipline", "code-quality", "refactor-safety", "security"],
    "tester": ["workflow-discipline", "testing", "debugging"],
}

_FORBIDDEN_PHRASES = [
    "implémentation terminée",
    "syntaxe valide",
    "changements appliqués",
    "all changes are in place",
]

_REQUIRED_SECTIONS = [
    "contexte",
    "objectif",
    "inclus",
    "hors scope",
    "critères d'acceptation",
]

_MIN_WORD_COUNT = 100


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
    return [Path("prompts") / name for name in names]


def find_prompt(ticket_id: str, step: str) -> Path:
    for candidate in prompt_candidates(ticket_id, step):
        if candidate.exists():
            return candidate
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


def execute_external_command(command_text: str, prompt_content: str) -> tuple[str, str, int]:
    command = shlex.split(command_text)
    if not command:
        raise RunnerError("external command must not be empty")
    completed = subprocess.run(
        command,
        input=prompt_content,
        text=True,
        capture_output=True,
        shell=False,
        check=False,
    )
    return completed.stdout, completed.stderr, completed.returncode


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log_runtime(ticket_id: str, message: str) -> None:
    log_path = Path("runs") / ticket_id / "runtime.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"[{_now_iso()}] {message}\n")


def compose_runtime_prompt(ticket_id: str, step: str, task_content: str) -> str:
    """Compose full runtime prompt: GLOBAL CONTEXT + ROLE + SKILLS + TASK."""
    sections: list[tuple[str, str]] = []

    global_ctx_path = Path(GLOBAL_CONTEXT_FILE)
    if global_ctx_path.exists():
        sections.append(("GLOBAL CONTEXT", global_ctx_path.read_text(encoding="utf-8")))
        _log_runtime(ticket_id, f"compose: global-context={global_ctx_path}")
    else:
        _log_runtime(ticket_id, f"compose: global-context not found at {global_ctx_path} — skipped")

    role_file = STEP_ROLE_FILES.get(step)
    if role_file:
        role_path = Path(role_file)
        if role_path.exists():
            sections.append(("ROLE", role_path.read_text(encoding="utf-8")))
            _log_runtime(ticket_id, f"compose: role={role_path}")
        else:
            _log_runtime(ticket_id, f"compose: role not found at {role_path} — skipped")

    for skill_name in STEP_SKILL_FILES.get(step, []):
        skill_path = Path("ai/skills") / f"{skill_name}.md"
        if skill_path.exists():
            sections.append((f"SKILL: {skill_name}", skill_path.read_text(encoding="utf-8")))
            _log_runtime(ticket_id, f"compose: skill={skill_path}")
        else:
            _log_runtime(ticket_id, f"compose: skill not found at {skill_path} — skipped")

    sections.append(("TASK", task_content))
    _log_runtime(ticket_id, "compose: task (canonical prompt)")

    parts = [f"# {label}\n\n{content.strip()}" for label, content in sections]
    return "\n\n---\n\n".join(parts)


def validate_planner_output(content: str) -> list[str]:
    """Return rejection reasons; empty list means the output is valid."""
    reasons: list[str] = []
    stripped = content.strip()

    word_count = len(stripped.split())
    if word_count < _MIN_WORD_COUNT:
        reasons.append(f"plan trop court ({word_count} mots, minimum {_MIN_WORD_COUNT})")

    lower = stripped.lower()
    for phrase in _FORBIDDEN_PHRASES:
        if phrase in lower:
            reasons.append(f"phrase interdite: «{phrase}»")

    for section in _REQUIRED_SECTIONS:
        if section not in lower:
            reasons.append(f"section manquante: «{section}»")

    return reasons


def show_next(ticket_id: str) -> None:
    step = read_next_step(ticket_id)
    if step == "done":
        print("Workflow complete.")
        return
    prompt_path = find_prompt(ticket_id, step)
    output_path = default_output_path(ticket_id, step)
    print(f"Next step: {step}")
    print(f"Prompt: {prompt_path}")
    print(f"Expected output: {output_path}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one ai-dev-factory ticket step locally.")
    parser.add_argument("ticket_id", help="Ticket id, for example T002")
    parser.add_argument("step", nargs="?", help="Step, for example planner, coder, review")
    parser.add_argument("--show-prompt", action="store_true", help="Print the canonical prompt to stdout")
    parser.add_argument("--next", action="store_true", help="Show the next workflow step")
    parser.add_argument("--exec-cmd", help="Run an explicit external command, passing the prompt on stdin")
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
        help="Relative path to a file appended to the canonical prompt when using --exec-cmd",
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
        prompt_path = find_prompt(ticket_id, step)
        prompt_content = prompt_path.read_text(encoding="utf-8")

        if args.show_prompt:
            print(prompt_content)

        if args.exec_cmd:
            effective_prompt = compose_runtime_prompt(ticket_id, step, prompt_content)
            if args.extra_context_file:
                extra_path = ensure_safe_relative_path(args.extra_context_file)
                if not extra_path.exists():
                    raise RunnerError(f"extra-context-file not found: {extra_path}")
                extra_content = extra_path.read_text(encoding="utf-8")
                effective_prompt = (
                    effective_prompt
                    + "\n\n---\n\n## Contexte de retry injecté par run_ticket.py\n\n"
                    + extra_content
                )
                _log_runtime(ticket_id, f"compose: extra-context={args.extra_context_file}")
            stdout, stderr, return_code = execute_external_command(args.exec_cmd, effective_prompt)
            if args.output_path:
                output_path = ensure_safe_relative_path(args.output_path)
            else:
                output_path = default_output_path(ticket_id, step)
            write_output(output_path, stdout)
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
