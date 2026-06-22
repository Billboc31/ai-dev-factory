"""Static isolation test — execution_rules_engine must not touch approval tables (T201).

The engine's approval state is resolved exclusively through
``get_execution_approval_state`` which wraps
``ticket_approval_service.compute_execution_eligibility``. The engine MUST NOT
reference the underlying approval table or status column directly, anywhere in
non-comment code.
"""

from __future__ import annotations

import re
from pathlib import Path


_ENGINE_PATH = (
    Path(__file__).parent.parent / "tools" / "agent_runner" / "execution_rules_engine.py"
)

_FORBIDDEN_SUBSTRINGS = ("ticket_approvals", "approval_status")


def _strip_comments_and_docstrings(source: str) -> str:
    """Naively strip Python comments and triple-quoted strings.

    Good enough for substring auditing: it removes ``# ...`` line comments and
    text inside ``\"\"\"...\"\"\"`` / ``'''...'''`` blocks. Substrings appearing
    inside ordinary string literals still count as "in code", which is the
    intended audit (the engine must not even mention those names as data).
    """
    # Remove triple-quoted blocks (greedy across newlines).
    source = re.sub(r'"""[\s\S]*?"""', "", source)
    source = re.sub(r"'''[\s\S]*?'''", "", source)
    # Remove line comments.
    source = re.sub(r"#[^\n]*", "", source)
    return source


def test_engine_does_not_reference_approval_tables() -> None:
    raw = _ENGINE_PATH.read_text(encoding="utf-8")
    stripped = _strip_comments_and_docstrings(raw)
    for forbidden in _FORBIDDEN_SUBSTRINGS:
        assert forbidden not in stripped, (
            f"execution_rules_engine.py must not reference {forbidden!r} "
            "outside of comments — approval state must flow through "
            "get_execution_approval_state -> compute_execution_eligibility."
        )


def test_engine_routes_approval_through_compute_execution_eligibility() -> None:
    raw = _ENGINE_PATH.read_text(encoding="utf-8")
    assert "compute_execution_eligibility" in raw, (
        "execution_rules_engine.py must read the approval state via "
        "ticket_approval_service.compute_execution_eligibility."
    )
