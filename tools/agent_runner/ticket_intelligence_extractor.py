"""Deterministic feature extractor for Ticket Intelligence analysis.

Pure Python — no AI, no network calls, no side effects.
Returns a dict of computed signals from raw ticket text.
These signals are fed to the AI analyzer as pre-computed context.
"""

from __future__ import annotations

import re

RISKY_KEYWORDS = [
    "database",
    "migration",
    "scheduler",
    "auth",
    "security",
    "deployment",
    "multi-project",
    "worker",
    "daemon",
]

DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "backend": ["api", "endpoint", "fastapi", "route", "backend", "server", "python", "service"],
    "frontend": ["react", "jsx", "dashboard", "component", "page", "frontend", "css", "html", "ui"],
    "database": ["database", "db", "table", "schema", "migration", "sql", "sqlite", "postgres"],
    "infra": ["docker", "compose", "deploy", "infra", "container", "nginx", "traefik"],
    "orchestration": ["scheduler", "daemon", "worker", "orchestrat", "queue", "dispatch", "pipeline"],
    "UI": ["button", "panel", "display", "render", "modal", "form", "badge", "label"],
    "tests": ["test", "pytest", "vitest", "jest", "coverage", "fixture", "mock"],
}

_DEPENDENCY_PATTERNS = [
    r"\bdepends?\s+on\b",
    r"\bafter\s+T\d+\b",
    r"\brequires?\b",
    r"\bblocked?\s+by\b",
]

_TICKET_ID_RE = re.compile(r"\bT\d{3,}\b")

_SCHEDULER_KEYWORDS = {"scheduler", "daemon", "worker", "dispatch", "queue", "run_daemon"}
_DB_MIGRATION_KEYWORDS = {"migration", "schema", "alter table", "create table", "add column", "drop column"}


def extract(ticket_text: str) -> dict:
    """Extract deterministic signals from ticket text.

    Returns a plain dict that is JSON-serialisable.
    """
    lower = ticket_text.lower()

    text_length = len(ticket_text)

    # Bullet-point lines as a rough requirement count
    requirement_count = len(re.findall(r"^[-*]\s+\S", ticket_text, re.MULTILINE))

    # Acceptance criteria count: items under the acceptance criteria heading
    acceptance_criteria_count = 0
    ac_match = re.search(
        r"##\s*acceptance criteria(.*?)(?=\n##|\Z)", lower, re.DOTALL | re.IGNORECASE
    )
    if ac_match:
        acceptance_criteria_count = len(
            re.findall(r"^[-*]\s+\S", ac_match.group(1), re.MULTILINE)
        )

    risky_keywords_found = [kw for kw in RISKY_KEYWORDS if kw in lower]

    affected_domains = [
        domain
        for domain, keywords in DOMAIN_KEYWORDS.items()
        if any(kw in lower for kw in keywords)
    ]

    dependency_hint_count = sum(
        len(re.findall(pat, lower)) for pat in _DEPENDENCY_PATTERNS
    )

    referenced_ticket_ids = sorted(set(_TICKET_ID_RE.findall(ticket_text)))

    # ~4 chars per token (rough heuristic)
    estimated_token_size = text_length // 4

    # Rough file-impact: number of distinct risky domains touched
    rough_file_impact = len(risky_keywords_found) + len(affected_domains)

    changes_scheduler = any(kw in lower for kw in _SCHEDULER_KEYWORDS)

    likely_needs_db_migration = any(kw in lower for kw in _DB_MIGRATION_KEYWORDS)

    return {
        "text_length": text_length,
        "requirement_count": requirement_count,
        "acceptance_criteria_count": acceptance_criteria_count,
        "risky_keywords_found": risky_keywords_found,
        "affected_domains": affected_domains,
        "dependency_hint_count": dependency_hint_count,
        "referenced_ticket_ids": referenced_ticket_ids,
        "estimated_token_size": estimated_token_size,
        "rough_file_impact": rough_file_impact,
        "changes_scheduler": changes_scheduler,
        "likely_needs_db_migration": likely_needs_db_migration,
    }
