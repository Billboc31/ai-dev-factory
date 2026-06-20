"""Unit tests for the deterministic ticket intelligence feature extractor (T197)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from ticket_intelligence_extractor import extract


SIMPLE_TICKET = """
# T001 — Add hello endpoint

## Description

Add a simple GET /hello endpoint to the FastAPI backend.

## Acceptance criteria

- GET /hello returns 200
- Response body is {"message": "hello"}
"""

COMPLEX_TICKET = """
# T197 — Add advisory ticket intelligence analysis before development cycle

## Description

Add a hybrid (deterministic + AI) analysis step.

This ticket requires:
- database migration for new ticket_intelligence table
- backend API endpoints
- frontend UI panel
- worker daemon integration
- scheduler-aware analysis
- auth token handling for security

## Acceptance criteria

- analysis stored in database
- GET /api/tickets/:id/intelligence returns analysis
- POST /api/tickets/:id/intelligence/analyze triggers analysis
- UI shows advisory badge

Depends on T001, T042. Blocked by T010.
"""


def test_extract_returns_dict():
    result = extract(SIMPLE_TICKET)
    assert isinstance(result, dict)


def test_text_length():
    result = extract(SIMPLE_TICKET)
    assert result["text_length"] == len(SIMPLE_TICKET)


def test_estimated_token_size():
    result = extract(SIMPLE_TICKET)
    assert result["estimated_token_size"] == len(SIMPLE_TICKET) // 4


def test_acceptance_criteria_count():
    result = extract(SIMPLE_TICKET)
    assert result["acceptance_criteria_count"] == 2


def test_acceptance_criteria_count_complex():
    result = extract(COMPLEX_TICKET)
    assert result["acceptance_criteria_count"] == 4


def test_risky_keywords_simple():
    result = extract(SIMPLE_TICKET)
    assert result["risky_keywords_found"] == []


def test_risky_keywords_complex():
    result = extract(COMPLEX_TICKET)
    found = result["risky_keywords_found"]
    assert "database" in found
    assert "scheduler" in found
    assert "auth" in found
    assert "daemon" in found
    assert "worker" in found


def test_affected_domains_backend():
    result = extract(SIMPLE_TICKET)
    assert "backend" in result["affected_domains"]


def test_affected_domains_complex():
    result = extract(COMPLEX_TICKET)
    domains = result["affected_domains"]
    assert "backend" in domains
    assert "database" in domains
    assert "frontend" in domains


def test_dependency_hints_none():
    result = extract(SIMPLE_TICKET)
    assert result["dependency_hint_count"] == 0


def test_dependency_hints_found():
    result = extract(COMPLEX_TICKET)
    assert result["dependency_hint_count"] >= 2


def test_referenced_ticket_ids():
    result = extract(COMPLEX_TICKET)
    ids = result["referenced_ticket_ids"]
    assert "T001" in ids
    assert "T042" in ids
    assert "T010" in ids
    assert "T197" in ids


def test_no_extra_referenced_tickets_in_simple():
    # SIMPLE_TICKET's own ID (T001) appears in the title — that's expected
    result = extract(SIMPLE_TICKET)
    assert result["referenced_ticket_ids"] == ["T001"]


def test_changes_scheduler_false():
    result = extract(SIMPLE_TICKET)
    assert result["changes_scheduler"] is False


def test_changes_scheduler_true():
    result = extract(COMPLEX_TICKET)
    assert result["changes_scheduler"] is True


def test_likely_needs_db_migration_false():
    result = extract(SIMPLE_TICKET)
    assert result["likely_needs_db_migration"] is False


def test_likely_needs_db_migration_true():
    result = extract(COMPLEX_TICKET)
    assert result["likely_needs_db_migration"] is True


def test_rough_file_impact_simple():
    result = extract(SIMPLE_TICKET)
    # Has backend domain, no risky keywords
    assert result["rough_file_impact"] >= 1


def test_rough_file_impact_complex_higher():
    simple = extract(SIMPLE_TICKET)
    complex_ = extract(COMPLEX_TICKET)
    assert complex_["rough_file_impact"] > simple["rough_file_impact"]


def test_empty_ticket():
    result = extract("")
    assert result["text_length"] == 0
    assert result["risky_keywords_found"] == []
    assert result["affected_domains"] == []
    assert result["changes_scheduler"] is False
    assert result["likely_needs_db_migration"] is False


def test_all_required_keys_present():
    result = extract(SIMPLE_TICKET)
    required = {
        "text_length", "requirement_count", "acceptance_criteria_count",
        "risky_keywords_found", "affected_domains", "dependency_hint_count",
        "referenced_ticket_ids", "estimated_token_size", "rough_file_impact",
        "changes_scheduler", "likely_needs_db_migration",
    }
    assert required.issubset(result.keys())
