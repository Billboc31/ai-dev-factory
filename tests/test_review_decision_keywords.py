"""Tests for T015 — dynamic review decision keyword injection."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_ticket import (
    REVIEW_DECISION_KEYWORDS,
    TRANSITIONS,
    _build_review_decision_context_file,
    _determine_next_state,
)


# ── REVIEW_DECISION_KEYWORDS coherence with TRANSITIONS ──────────────────────

def test_review_keywords_cover_all_review_states():
    review_states = {s for s, t in TRANSITIONS.items() if t and t[0] == "review"}
    assert review_states == set(REVIEW_DECISION_KEYWORDS)


def test_review_keywords_approve_is_valid_next():
    for state, kws in REVIEW_DECISION_KEYWORDS.items():
        possible_next = TRANSITIONS[state][2]
        assert kws["approve"] in possible_next, (
            f"{state}: approve keyword {kws['approve']!r} not in TRANSITIONS possible_next {possible_next}"
        )


def test_review_keywords_fix_is_valid_next():
    for state, kws in REVIEW_DECISION_KEYWORDS.items():
        possible_next = TRANSITIONS[state][2]
        assert kws["fix"] in possible_next, (
            f"{state}: fix keyword {kws['fix']!r} not in TRANSITIONS possible_next {possible_next}"
        )


def test_plan_review_keywords():
    kws = REVIEW_DECISION_KEYWORDS["PLAN_REVIEW_NEEDED"]
    assert kws["approve"] == "PLAN_APPROVED"
    assert kws["fix"] == "PLAN_FIX_REQUIRED"


def test_implementation_review_keywords():
    kws = REVIEW_DECISION_KEYWORDS["IMPLEMENTATION_REVIEW_NEEDED"]
    assert kws["approve"] == "IMPLEMENTATION_APPROVED"
    assert kws["fix"] == "IMPLEMENTATION_FIX_REQUIRED"


# ── _build_review_decision_context_file ──────────────────────────────────────

def _run_with_tmpdir(state: str) -> tuple[Path, str]:
    with tempfile.TemporaryDirectory() as tmp:
        ticket_id = "T999"
        run_dir = Path(tmp) / "runs" / ticket_id / "reviews"
        run_dir.mkdir(parents=True)

        orig_cwd = Path.cwd()
        import os
        os.chdir(tmp)
        try:
            ctx_path = _build_review_decision_context_file(ticket_id, state)
            content = ctx_path.read_text(encoding="utf-8")
        finally:
            os.chdir(orig_cwd)
    return ctx_path, content


def test_plan_review_context_file_contains_approve_keyword():
    _, content = _run_with_tmpdir("PLAN_REVIEW_NEEDED")
    assert "PLAN_APPROVED" in content


def test_plan_review_context_file_contains_fix_keyword():
    _, content = _run_with_tmpdir("PLAN_REVIEW_NEEDED")
    assert "PLAN_FIX_REQUIRED" in content


def test_implementation_review_context_file_contains_approve_keyword():
    _, content = _run_with_tmpdir("IMPLEMENTATION_REVIEW_NEEDED")
    assert "IMPLEMENTATION_APPROVED" in content


def test_implementation_review_context_file_contains_fix_keyword():
    _, content = _run_with_tmpdir("IMPLEMENTATION_REVIEW_NEEDED")
    assert "IMPLEMENTATION_FIX_REQUIRED" in content


def test_plan_review_context_file_does_not_contain_implementation_keywords():
    _, content = _run_with_tmpdir("PLAN_REVIEW_NEEDED")
    assert "IMPLEMENTATION_APPROVED" not in content
    assert "IMPLEMENTATION_FIX_REQUIRED" not in content


def test_implementation_review_context_file_does_not_contain_plan_keywords():
    _, content = _run_with_tmpdir("IMPLEMENTATION_REVIEW_NEEDED")
    assert "PLAN_APPROVED" not in content
    assert "PLAN_FIX_REQUIRED" not in content


def test_context_file_path_contains_state_name():
    with tempfile.TemporaryDirectory() as tmp:
        ticket_id = "T999"
        import os
        os.chdir(tmp)
        try:
            ctx_path = _build_review_decision_context_file(ticket_id, "PLAN_REVIEW_NEEDED")
        finally:
            os.chdir(Path(__file__).parent.parent)
    assert "PLAN_REVIEW_NEEDED" in ctx_path.name


# ── No injection for non-review states ───────────────────────────────────────

def test_non_review_states_not_in_review_decision_keywords():
    non_review_states = {s for s, t in TRANSITIONS.items() if t and t[0] != "review"}
    for state in non_review_states:
        assert state not in REVIEW_DECISION_KEYWORDS, (
            f"state {state!r} (step={TRANSITIONS[state][0]!r}) must not appear in REVIEW_DECISION_KEYWORDS"
        )


# ── _determine_next_state parsing unchanged ───────────────────────────────────

def test_determine_next_state_plan_approved():
    possible = ["PLAN_APPROVED", "PLAN_FIX_REQUIRED"]
    assert _determine_next_state(False, "some text\nPLAN_APPROVED\nmore", possible) == "PLAN_APPROVED"


def test_determine_next_state_plan_fix_required():
    possible = ["PLAN_APPROVED", "PLAN_FIX_REQUIRED"]
    assert _determine_next_state(False, "PLAN_FIX_REQUIRED", possible) == "PLAN_FIX_REQUIRED"


def test_determine_next_state_implementation_approved():
    possible = ["IMPLEMENTATION_APPROVED", "IMPLEMENTATION_FIX_REQUIRED"]
    assert _determine_next_state(False, "\nIMPLEMENTATION_APPROVED\n", possible) == "IMPLEMENTATION_APPROVED"


def test_determine_next_state_no_keyword_returns_none():
    possible = ["IMPLEMENTATION_APPROVED", "IMPLEMENTATION_FIX_REQUIRED"]
    assert _determine_next_state(False, "no keyword here", possible) == None


def test_determine_next_state_wrong_keyword_returns_none():
    possible = ["IMPLEMENTATION_APPROVED", "IMPLEMENTATION_FIX_REQUIRED"]
    assert _determine_next_state(False, "PLAN_APPROVED", possible) == None


def test_determine_next_state_deterministic_ignores_output():
    assert _determine_next_state(True, "", ["PLAN_REVIEW_NEEDED"]) == "PLAN_REVIEW_NEEDED"
    assert _determine_next_state(True, "garbage", ["IMPLEMENTATION_REVIEW_NEEDED"]) == "IMPLEMENTATION_REVIEW_NEEDED"


# ── T027 — tolerant review keyword parsing ────────────────────────────────────

def test_determine_next_state_bold_markdown_approved():
    possible = ["PLAN_APPROVED", "PLAN_FIX_REQUIRED"]
    assert _determine_next_state(False, "**PLAN_APPROVED**", possible) == "PLAN_APPROVED"


def test_determine_next_state_bold_markdown_fix_required():
    possible = ["IMPLEMENTATION_APPROVED", "IMPLEMENTATION_FIX_REQUIRED"]
    assert _determine_next_state(False, "**IMPLEMENTATION_FIX_REQUIRED**", possible) == "IMPLEMENTATION_FIX_REQUIRED"


def test_determine_next_state_verdict_label():
    possible = ["IMPLEMENTATION_APPROVED", "IMPLEMENTATION_FIX_REQUIRED"]
    assert _determine_next_state(False, "Verdict : IMPLEMENTATION_FIX_REQUIRED", possible) == "IMPLEMENTATION_FIX_REQUIRED"


def test_determine_next_state_decision_accented_label():
    possible = ["PLAN_APPROVED", "PLAN_FIX_REQUIRED"]
    assert _determine_next_state(False, "Décision : PLAN_APPROVED", possible) == "PLAN_APPROVED"


def test_determine_next_state_decision_unaccented_label():
    possible = ["IMPLEMENTATION_APPROVED", "IMPLEMENTATION_FIX_REQUIRED"]
    assert _determine_next_state(False, "Decision: IMPLEMENTATION_APPROVED", possible) == "IMPLEMENTATION_APPROVED"


def test_determine_next_state_verdict_mid_text():
    possible = ["PLAN_APPROVED", "PLAN_FIX_REQUIRED"]
    text = "Some review comments here.\n\nVerdict : PLAN_FIX_REQUIRED\n\nSee above."
    assert _determine_next_state(False, text, possible) == "PLAN_FIX_REQUIRED"


def test_determine_next_state_bold_wrong_keyword_ignored():
    possible = ["IMPLEMENTATION_APPROVED", "IMPLEMENTATION_FIX_REQUIRED"]
    assert _determine_next_state(False, "**PLAN_APPROVED**", possible) is None


def test_determine_next_state_verdict_wrong_keyword_ignored():
    possible = ["IMPLEMENTATION_APPROVED", "IMPLEMENTATION_FIX_REQUIRED"]
    assert _determine_next_state(False, "Verdict : PLAN_FIX_REQUIRED", possible) is None
