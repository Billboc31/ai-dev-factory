## Objective

Make `PLAN_FIX_REQUIRED` regenerations reliably rewrite the target artifact (`runs/Txxx/plan.md`) instead of producing a meta-report describing the rewrite. This is achieved by reinforcing planner prompts during fix mode, adding a lightweight artifact-type-aware "meta-report" heuristic to the validator, and giving the runner a single retry with an explicit artifact-only reinforcement before failing the step.

## Included

- `prompts/generic/planner.md`: append (or, in a small new section) an explicit "your response will be written verbatim to `runs/<ticket>/plan.md`; rewrite the artifact itself, do not summarize what changed, do not produce a status report" block. Keep wording compatible with first-pass planning (it must apply to both initial plans and rewrites).
- `tools/agent_runner/run_ticket.py` — `_build_fix_context_file()` (or the call site at line ~1067): prepend a short fix-mode preamble making the artifact-only rule unmistakable when `current_state == "PLAN_FIX_REQUIRED"` ("rewrite the artifact, do not describe modifications"). The preamble must reference the target artifact path explicitly.
- `tools/agent_runner/run_step.py` — `validate_planner_output()`:
  - Add an `artifact_type: str = "plan"` parameter (groundwork for the `plan / review / fix / code / ADR` typology mentioned in the ticket; only `plan` is wired now).
  - Add a small, high-precision `_looks_like_meta_report(content)` helper. It must trigger only when the *overall* file reads as a report — for example: opening sentence matches a curated regex set (`^the plan`, `^this plan`, `^plan rewritten`, `^key points covered`, `^the document now`, `^the artifact (?:was|has been) (?:rewritten|updated)`, etc.) **and** the file has no fenced code block / file path / bullet list of changes. Single matching sentences inside an otherwise structured plan must not trigger.
  - When the heuristic triggers, append a dedicated reason (e.g. `"plan looks like a meta-report, not the artifact itself"`) so the runner can distinguish this case.
- `tools/agent_runner/run_ticket.py` — planner branch around lines 1086–1101:
  - If `reasons` contains the new meta-report reason and no retry has been attempted yet for this state transition, retry the planner step **once** with an `extra_context_file` carrying the explicit artifact-only instruction (a small file generated next to the fix context, or appended to it). Log `runtime warning: planner_meta_report_retry`.
  - On second failure (or any other reason), keep the current behaviour: log `runtime failure: planner_invalid` and return rc=2.
- `tests/test_validate_planner_output.py`:
  - Add a test reproducing the T201 failure mode: a file whose entire content starts with "The plan has been rewritten…" / "Key points covered…" with no fenced code blocks or file paths — must be rejected with the meta-report reason.
  - Add a counter-test: a structured plan that *contains* the sentence "The plan now ensures X" inside a section must still pass (guards against false positives).
- `tests/test_planner_recovery.py`: add a unit test that exercises the new "retry once on meta-report" path — first call returns a meta-report, second call returns a valid plan, runner ends with rc=0 and the right log lines.

## Excluded

- Reintroducing strict template enforcement (exact section order, exact wording, hard rejection of non-canonical synonyms). The four-heading requirement of the generic prompt is already enforced advisorily by the prompt itself; we are not making it a validator-side hard check.
- Wiring artifact-type-aware validation for `review`, `fix`, `code`, `ADR`. Only the `artifact_type="plan"` path is implemented; the parameter is added so future tickets can extend it without churn.
- Changing the daemon-level retry policy / `_RETRY_POLICIES` in `run_daemon`. The new retry is local to the planner step in `run_ticket.py`.
- Modifying coder, reviewer, or tester roles, prompts, or validators.
- Reverting the existing permissive behaviour (trivial plans with a single recognised section, plans in either FR or EN, forbidden-phrase tolerance inside code blocks).
- Editing `runs/T201/**` historical artifacts; only new tests reproduce the failure mode.

## Acceptance criteria

- A new test in `tests/test_validate_planner_output.py` reproduces the T201 meta-report opening (e.g. starts with `The plan has been rewritten…`) and `validate_planner_output` returns a non-empty `reasons` list containing the meta-report reason.
- An additional test confirms that a structured plan mentioning a meta-report-like phrase inside a section is **not** rejected (no false positive).
- `prompts/generic/planner.md` contains explicit "rewrite the artifact, do not describe modifications, do not produce a status report" wording, and the fix-mode context built by `_build_fix_context_file()` repeats this instruction with the concrete target path when state is `PLAN_FIX_REQUIRED`.
- When the planner produces a meta-report under `PLAN_FIX_REQUIRED`, `run_ticket.py` retries the planner step exactly once with a reinforced artifact-only context before logging `runtime failure: planner_invalid`. A test in `tests/test_planner_recovery.py` covers this retry-once path and asserts the log line ordering.
- All existing tests in `tests/test_validate_planner_output.py` and `tests/test_planner_recovery.py` still pass unchanged, including the bilingual and trivial-ticket cases.
- The validator signature change is backward compatible: callers that do not pass `artifact_type` keep their current behaviour (`artifact_type="plan"` by default).
