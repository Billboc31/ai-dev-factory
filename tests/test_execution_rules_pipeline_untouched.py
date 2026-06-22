"""Static guard — execution pipeline must not import the rules engine (T201).

The Rules Engine is advisory. The scheduler/daemon and per-ticket runner must
continue to schedule tickets exactly as before, with no awareness of rule
evaluation.
"""

from __future__ import annotations

from pathlib import Path


_AGENT_RUNNER = Path(__file__).parent.parent / "tools" / "agent_runner"

_FORBIDDEN_SYMBOLS = ("execution_rules_engine", "evaluate_ticket")


def _scan(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def test_run_daemon_does_not_import_engine() -> None:
    src = _scan(_AGENT_RUNNER / "run_daemon.py")
    for symbol in _FORBIDDEN_SYMBOLS:
        assert symbol not in src, (
            f"run_daemon.py must not reference {symbol!r} — the rules engine "
            "is advisory and the scheduler/daemon must remain unchanged."
        )


def test_run_ticket_does_not_import_engine() -> None:
    src = _scan(_AGENT_RUNNER / "run_ticket.py")
    for symbol in _FORBIDDEN_SYMBOLS:
        assert symbol not in src, (
            f"run_ticket.py must not reference {symbol!r} — the rules engine "
            "is advisory and per-ticket execution must remain unchanged."
        )


def test_no_other_pipeline_module_imports_engine() -> None:
    """No other agent-runner orchestration module may import the engine."""
    orchestration_files = [
        _AGENT_RUNNER / "run_daemon.py",
        _AGENT_RUNNER / "run_ticket.py",
        _AGENT_RUNNER / "run_step.py",
    ]
    for path in orchestration_files:
        if not path.exists():
            continue
        src = _scan(path)
        for symbol in _FORBIDDEN_SYMBOLS:
            assert symbol not in src, (
                f"{path.name} must not reference {symbol!r}; rule evaluation "
                "must not influence the execution pipeline."
            )
