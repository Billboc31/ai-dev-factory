"""Ticket Intelligence execution stage constants (T210).

Each stage names a precise position in the analyzer pipeline. The value is
persisted in ``ticket_intelligence.stage`` and surfaced in the API + UI so
operators can tell exactly where a stuck analysis is blocked without grepping
the logs.

This module deliberately only exports constants — no helpers that would force
callers to share a single ``runtime_db`` binding, which makes the analyzer's
test-time monkeypatching of ``runtime_db`` straightforward.
"""

from __future__ import annotations

STAGE_QUEUED = "queued"
STAGE_STARTING = "starting"
STAGE_BUILDING_PROMPT = "building_prompt"
STAGE_WAITING_AI = "waiting_ai"
STAGE_PARSING_RESULT = "parsing_result"
STAGE_PERSISTING = "persisting"
STAGE_COMPLETED = "completed"
STAGE_FAILED = "failed"

ORDERED_STAGES = (
    STAGE_QUEUED,
    STAGE_STARTING,
    STAGE_BUILDING_PROMPT,
    STAGE_WAITING_AI,
    STAGE_PARSING_RESULT,
    STAGE_PERSISTING,
    STAGE_COMPLETED,
)
