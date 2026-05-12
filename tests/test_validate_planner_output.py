"""Tests unitaires pour validate_planner_output()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_step import validate_planner_output


def _make_plan(sections: list[str], extra: str = "") -> str:
    body = " word" * 120
    return "\n\n".join(sections) + "\n\n" + body + "\n\n" + extra


CANONICAL = [
    "## contexte",
    "## objectif",
    "## inclus",
    "## hors scope",
    "## critères d'acceptation",
]

SYNONYMS = [
    "## contexte technique",
    "## objectifs",
    "## scope",
    "## non inclus",
    "## acceptance criteria",
]


def test_valid_canonical():
    assert validate_planner_output(_make_plan(CANONICAL)) == []


def test_valid_synonyms():
    assert validate_planner_output(_make_plan(SYNONYMS)) == []


def test_too_short():
    short = "\n\n".join(CANONICAL) + "\n\ncourt"
    reasons = validate_planner_output(short)
    assert any("plan trop court" in r for r in reasons)


def test_missing_section_is_not_blocking_anymore():
    sections = [s for s in CANONICAL if "hors scope" not in s]
    reasons = validate_planner_output(_make_plan(sections))
    assert reasons == []


def test_forbidden_phrase_real():
    plan = _make_plan(CANONICAL, extra="implémentation terminée")
    reasons = validate_planner_output(plan)
    assert any("phrase interdite" in r for r in reasons)


def test_forbidden_phrase_in_code_block():
    plan = _make_plan(CANONICAL, extra="```\nimplémentation terminée\n```")
    assert validate_planner_output(plan) == []
