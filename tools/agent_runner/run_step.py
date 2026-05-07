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
    parser.add_argument("--stderr-log", help="Relative path where stderr should be written")
    parser.add_argument(
        "--write-output",
        nargs="?",
        const="__DEFAULT__",
        help="Write stdin to an artifact path. If no path is provided, use the default for the step.",
    )
    parser.add_argument("--set-status", help="Append a workflow status to runs/TXXX/workflow-status.md")
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
            stdout, stderr, return_code = execute_external_command(args.exec_cmd, prompt_content)
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
