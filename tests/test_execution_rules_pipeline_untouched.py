"""Static guard — execution pipeline must not import the rules engine (T201).

The Rules Engine is advisory: its ``evaluate_ticket`` decision must never
drive execution. The scheduler/daemon and per-ticket runner must continue to
schedule tickets exactly as before, with no awareness of the advisory
eligibility verdict.

Exception (T223): ``run_ticket`` is allowed to call
``execution_rules_engine.is_human_plan_approval_required`` — a *read-only*
lookup of a single project rule that gates the human plan-approval step. This
does not run the advisory eligibility evaluator; it only consults the stored
value of one specific rule.
"""

from __future__ import annotations

from pathlib import Path


_AGENT_RUNNER = Path(__file__).parent.parent / "tools" / "agent_runner"

# ``evaluate_ticket`` is the advisory eligibility entry point and must remain
# absent from the pipeline. ``execution_rules_engine`` as a module reference is
# only allowed in ``run_ticket.py`` for the plan-approval gate lookup below.
_FORBIDDEN_SYMBOLS_ALL = ("execution_rules_engine", "evaluate_ticket")
_FORBIDDEN_SYMBOLS_RUN_TICKET = ("evaluate_ticket",)


def _scan(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8")


def test_run_daemon_does_not_import_engine() -> None:
    src = _scan(_AGENT_RUNNER / "run_daemon.py")
    for symbol in _FORBIDDEN_SYMBOLS_ALL:
        assert symbol not in src, (
            f"run_daemon.py must not reference {symbol!r} — the rules engine "
            "is advisory and the scheduler/daemon must remain unchanged."
        )


def test_run_ticket_does_not_evaluate_advisory_eligibility() -> None:
    src = _scan(_AGENT_RUNNER / "run_ticket.py")
    for symbol in _FORBIDDEN_SYMBOLS_RUN_TICKET:
        assert symbol not in src, (
            f"run_ticket.py must not reference {symbol!r} — the advisory "
            "eligibility evaluator must not influence per-ticket execution."
        )


def test_run_ticket_only_reads_plan_approval_rule() -> None:
    """``run_ticket`` may touch the engine only for the plan-approval lookup."""
    src = _scan(_AGENT_RUNNER / "run_ticket.py")
    if "execution_rules_engine" in src:
        assert "is_human_plan_approval_required" in src, (
            "run_ticket.py touches execution_rules_engine but does not read "
            "is_human_plan_approval_required — no other engine surface may be "
            "consumed by the pipeline."
        )


def test_no_other_pipeline_module_imports_engine() -> None:
    """Only run_ticket may consult the plan-approval rule; other modules cannot."""
    orchestration_files = [
        _AGENT_RUNNER / "run_daemon.py",
        _AGENT_RUNNER / "run_step.py",
    ]
    for path in orchestration_files:
        if not path.exists():
            continue
        src = _scan(path)
        for symbol in _FORBIDDEN_SYMBOLS_ALL:
            assert symbol not in src, (
                f"{path.name} must not reference {symbol!r}; rule evaluation "
                "must not influence the execution pipeline."
            )
