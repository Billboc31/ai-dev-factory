#!/usr/bin/env python3
"""Sequential ticket runner for ai-dev-factory."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RUN_STEP = ROOT / "run_step.py"


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        text=True,
        capture_output=True,
        check=False,
    )


def show_next(ticket_id: str) -> int:
    result = run_command([
        sys.executable,
        str(RUN_STEP),
        ticket_id,
        "--next",
    ])

    print(result.stdout)

    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode


def execute_once(ticket_id: str, step: str, command: str) -> int:
    result = run_command([
        sys.executable,
        str(RUN_STEP),
        ticket_id,
        step,
        "--exec-cmd",
        command,
    ])

    print(result.stdout)

    if result.stderr:
        print(result.stderr, file=sys.stderr)

    return result.returncode


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sequential ai-dev-factory ticket runner")
    parser.add_argument("ticket_id")
    parser.add_argument("--once", help="Execute a single explicit step")
    parser.add_argument("--exec-cmd", help="External command to execute")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)

    if args.once:
        if not args.exec_cmd:
            print("error: --exec-cmd is required with --once", file=sys.stderr)
            return 2

        return execute_once(args.ticket_id, args.once, args.exec_cmd)

    return show_next(args.ticket_id)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
