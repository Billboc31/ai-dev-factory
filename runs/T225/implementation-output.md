All four fixes are in place and verified. Here's a summary of what was done:

---

**P1 — Stub capabilities removed**
`rerun_intelligence` and `trigger_deployment` removed from `_WORKSPACE_CAPABILITIES` and `_WORKSPACE_SYSTEM_PROMPT`, and their stub branch in `_execute_workspace_capability` deleted. Confirming these actions can no longer result in a 500.

**P2 — Tests delivered** (`tests/test_supervisor_workspace.py`, 6 tests, all green)
- `test_unknown_capability_rejected` — capability not in allowlist → intent reset to informational, no pending action stored
- `test_forged_action_id_rejected` — unknown action_id → 404
- `test_action_id_project_mismatch_rejected` — valid action_id confirmed against wrong project → 403
- `test_functional_dev_creates_issue_draft_not_code` — functional_dev → draft stored, no action created
- `test_empty_issue_draft_rejected` — empty title/body on confirm → 422
- `test_ai_error_returns_generic_message` — error reply contains "unavailable", not provider details

**P3 — Generic error reply** (`main.py:3016`)
`f"AI call failed: {exc}"` replaced with `"The AI assistant is temporarily unavailable. Please try again in a moment."`. Exception still logged at ERROR with full traceback (`exc_info=True`).

**P4 — Structured ticket prefix** (`main.py:2967-2969`)
Ticket lines now use `- ticket "T001": {first_line}` format, making prompt injection syntactically harder to exploit.
