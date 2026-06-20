All 99 tests pass. Here's what was done to address the review:

**[BLOQUANT 1] — New file: `tests/test_ticket_intelligence_normalizer.py`** (58 tests across 7 test classes)
- `TestExtractJson`: 9 tests — plain JSON, markdown fences, preceded-by-text, empty/invalid inputs, whitespace
- `TestNormalizeScoreClamping`: 9 tests — out-of-range clamping (0→1, 11→10), defaults, invalid strings
- `TestNormalizeDifficultyLabel`: 11 tests — all 10 score bands auto-derived, explicit label preserved
- `TestNormalizeAutonomousRec`: 7 tests — all 4 valid values, invalid/None/missing → fallback
- `TestNormalizeCostEstimation`: 5 tests — present values preserved, fallback to `estimate_cost()`, unknown model
- `TestNormalizeListFields`: 7 tests — JSON serialization, non-list → `[]`, None → `[]`
- `TestNormalizeQueueRank` + `TestNormalizeBooleanFields` + `TestNormalizeFullPayload`

**[BLOQUANT 2]** — Already resolved: `apps/dashboard/tests/TicketIntelligencePanel.test.jsx` exists with 13 tests covering all required states.

**[MINEUR 1] — `intelligence.py:109`** — `except Exception` now captures `exc` and logs `logger.warning("could not read ticket.md for %s: %s", ticket_id, exc)`.

**[MINEUR 2] — `ticket_intelligence_analyzer.py`** — Added `_fill_template()` with a single-pass regex substitution (`_TEMPLATE_VARS_RE`), replacing the two chained `.replace()` calls. If ticket content contains `{{computed_signals}}`, it is no longer substituted in the second pass.
