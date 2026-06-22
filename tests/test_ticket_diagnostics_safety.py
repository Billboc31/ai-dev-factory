"""Safety tests for ticket_diagnostics: it must not import or call mutating
helpers from the agent runner. Diagnostics are read-only except for persisting
the diagnostic result itself.
"""

from __future__ import annotations

import importlib.util
import inspect
import re
import sys
from pathlib import Path

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_diagnostics():
    spec = importlib.util.spec_from_file_location(
        "_ticket_diagnostics_safety_test",
        _TOOLS / "ticket_diagnostics.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_diagnostics_does_not_import_destructive_modules():
    """The module's source must not import any of the agent runner's mutating
    entry points. This is a tripwire: adding such an import would be a clear
    signal that the diagnostic surface has grown beyond read-only.
    """
    src = (_TOOLS / "ticket_diagnostics.py").read_text(encoding="utf-8")
    forbidden_imports = [
        r"\bimport\s+run_ticket\b",
        r"\bimport\s+run_step\b",
        r"\bimport\s+run_daemon\b",
        r"\bimport\s+worktree_manager\b",
        r"\bimport\s+runtime_checkpoint\b",
        r"\bfrom\s+worktree_manager\s+import\b",
        r"\bfrom\s+runtime_checkpoint\s+import\b",
        r"\bfrom\s+run_ticket\s+import\b",
        r"\bfrom\s+run_step\s+import\b",
        r"\bfrom\s+run_daemon\s+import\b",
    ]
    for pattern in forbidden_imports:
        assert re.search(pattern, src) is None, f"forbidden import matches {pattern!r}"


def test_diagnostics_does_not_call_destructive_helpers():
    """Source must not reference known mutating helper names."""
    mod = _load_diagnostics()
    src = inspect.getsource(mod)
    forbidden_calls = [
        # worktree management mutations
        "worktree_manager.remove",
        "worktree_manager.delete",
        # checkpoint resets
        "runtime_checkpoint.reset",
        # approval mutations
        "ticket_approval_service.approve_execution",
        "ticket_approval_service.reject_execution",
        "ticket_approval_service.request_execution_approval",
        # runner / step mutations
        "run_ticket.",
        "run_step.",
        "run_daemon.",
        # destructive DB helpers
        "remove_worker(",
    ]
    for needle in forbidden_calls:
        assert needle not in src, f"forbidden call site found: {needle!r}"


def test_diagnostics_only_uses_safe_runtime_db_helpers():
    """The runtime_db calls invoked from ticket_diagnostics must be the read-only
    + persist-only set. No worker/runtime/state mutation may be performed.
    """
    src = (_TOOLS / "ticket_diagnostics.py").read_text(encoding="utf-8")
    runtime_db_calls = re.findall(r"runtime_db\.(\w+)", src)
    allowed = {
        # read-only reads
        "get_ticket_runtime",
        "get_ticket_intelligence",
        "get_ticket_readiness",
        "get_ticket_rule_evaluation",
        "get_latest_ticket_approval",
        "list_workers",
        # diagnostics persistence + timestamp helper
        "upsert_ticket_diagnostics",
        "_now_iso",
    }
    for call in runtime_db_calls:
        assert call in allowed, f"runtime_db.{call} is not in the safe allow-list"


def test_diagnostics_only_safe_approval_calls():
    """Only the read-only ``compute_execution_eligibility`` is allowed from the
    approval service.
    """
    src = (_TOOLS / "ticket_diagnostics.py").read_text(encoding="utf-8")
    approval_calls = re.findall(r"ticket_approval_service\.(\w+)", src)
    allowed = {"compute_execution_eligibility"}
    for call in approval_calls:
        assert call in allowed, (
            f"ticket_approval_service.{call} is not in the safe allow-list"
        )
