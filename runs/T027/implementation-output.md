237/237 pass. Here's a summary of what was implemented:

---

**Files modified:**
- `tools/agent_runner/run_ticket.py` — two changes:
  1. **`_determine_next_state`** (line 373): extended the regex from a single `^KEYWORD$` pattern to three alternatives: exact line, `**KEYWORD**` bold Markdown, and labelled forms (`Verdict : KEYWORD`, `Décision : KEYWORD`, `Decision: KEYWORD`). Guardrail unchanged — only keywords from `possible_next` are accepted.
  2. **New `_write_fix_artifact`** function (inserted before `_build_fix_context_file`): scans existing `fixes/plan-fix-*.md` or `fixes/implementation-fix-*.md`, increments N, writes the artifact with decision, review source path, review content, and timestamp. Explicit stdout print + runtime.log entry.
  3. **`auto_run`**: prints `auto-run: review keyword detected: <STATE>` to stdout on successful parse; calls `_write_fix_artifact` after `save_state` when `next_state.endswith("_FIX_REQUIRED")`.

**Files created:**
- `tests/test_fix_artifact.py` — 8 cases covering plan/implementation creation, correct N increment, content fields, and no artifact on `*_APPROVED` states.

**Files modified:**
- `tests/test_review_decision_keywords.py` — 8 new parsing tests covering bold Markdown, `Verdict :`, `Décision :`, `Decision:` forms, mid-text occurrence, and wrong-keyword guardrail under each form.
