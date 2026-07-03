"""Helpers for reading ticket conflict edges from dependency-analysis rows.

The global analyzer may declare ``CONFLICTING_SCOPE`` only in
``relationship_classifications`` while leaving ``conflicting_tickets`` empty.
Consumers (dispatcher, dashboard) must treat both sources as equivalent.
"""

from __future__ import annotations

CONFLICTING_SCOPE = "CONFLICTING_SCOPE"


def conflict_partners(
    ticket_id: str,
    analysis: dict | None,
    *,
    ticket_set: set[str],
) -> list[str]:
    """Return sorted ticket ids that conflict with ``ticket_id`` in ``ticket_set``."""
    if not analysis:
        return []
    partners: set[str] = set()
    for other in analysis.get("conflicting_tickets") or []:
        if other in ticket_set and other != ticket_id:
            partners.add(other)
    for rel in analysis.get("relationship_classifications") or []:
        if rel.get("type") != CONFLICTING_SCOPE:
            continue
        src, dst = rel.get("from"), rel.get("to")
        if src == ticket_id and dst in ticket_set and dst != ticket_id:
            partners.add(dst)
        elif dst == ticket_id and src in ticket_set and src != ticket_id:
            partners.add(src)
    return sorted(partners)


def build_conflict_map(
    ticket_ids: list[str],
    analyses: dict[str, dict],
) -> dict[str, set[str]]:
    """Build a symmetric conflict adjacency map for a batch."""
    ticket_set = set(ticket_ids)
    conflict_map: dict[str, set[str]] = {tid: set() for tid in ticket_ids}
    for ticket_id in ticket_ids:
        for other in conflict_partners(
            ticket_id, analyses.get(ticket_id), ticket_set=ticket_set,
        ):
            conflict_map[ticket_id].add(other)
            conflict_map[other].add(ticket_id)
    return conflict_map
