# T228 — Add autonomous “Unblock this ticket” recovery action to AI Workspace

**Source**: GitHub Issue #312

## Description

## Objective

Add an AI Workspace action that lets the user ask Claude to autonomously diagnose and recover a blocked AI Dev Factory ticket.

Example request:

> Unblock this ticket.

Claude should investigate why the active ticket is blocked, perform the authorized recovery work, restart the relevant pipeline step, and verify that the ticket is progressing again. If the blocker exposes an AI Dev Factory product bug, the action must create a documented GitHub issue.

## User story

As a remote AI Dev Factory user, I want to ask the integrated Workspace chat to unblock the current ticket so that Claude can inspect the pipeline, artifacts, logs, branches, and execution state without requiring me to diagnose each failure manually.

## Structured action

The Workspace should translate the request into a constrained Supervisor action similar to:

```json
{
  "action": "recover_ticket",
  "project_id": "ai-dev-factory",
  "ticket_id": "T226",
  "diagnose": true,
  "apply_safe_fixes": true,
  "retry_failed_stage": true,
  "create_bug_issue_when_detected": true
}
```

The active project and ticket must be resolved from the Workspace context when the user says “this ticket”.

## Recovery workflow

1. Collect the current ticket state.
2. Inspect the failed or blocked pipeline stage.
3. Read relevant logs and existing ticket artifacts.
4. Inspect repository and branch state when relevant.
5. Classify the blocker.
6. Produce a concise recovery plan.
7. Request confirmation before applying mutating recovery actions.
8. Apply only allowlisted and ticket-scoped fixes.
9. Retry the appropriate failed/blocked stage.
10. Verify that the ticket reaches the expected next state.
11. Return a recovery report to the chat.
12. When a reproducible AI Dev Factory bug is identified, create or link a GitHub issue containing the evidence.

## Blocker classification

The recovery agent must distinguish at least:

- missing or malformed ticket artifact;
- stale readiness or rule evaluation;
- missing human approval;
- failed planner, implementation, review, fix-loop, or test execution;
- branch divergence or missing remote update;
- repository working-tree conflict;
- transient provider, network, or process failure;
- invalid project configuration;
- unsupported or inconsistent pipeline state;
- reproducible AI Dev Factory product bug;
- blocker requiring an explicit user decision.

## Allowed recovery actions

Subject to Supervisor authorization and confirmation, the action may:

- regenerate a missing derived artifact using the expected repository convention;
- correct a malformed ticket-scoped artifact;
- refresh readiness and rule evaluation;
- fetch or pull the configured ticket branch using the approved strategy;
- restart or retry the failed pipeline stage;
- restart an approved local AI Dev Factory service when required;
- run ticket-scoped diagnostics and tests;
- create a GitHub bug issue with diagnostic evidence;
- add the created issue URL to the ticket recovery report.

## Safety requirements

- Route all actions through the Supervisor.
- Do not give Claude unrestricted shell access.
- Do not accept arbitrary paths, commands, service names, or internal endpoints from the frontend or model.
- Restrict mutations to the active ticket, its configured branch, approved artifacts, and allowlisted services.
- Never fabricate or bypass human approval.
- When the blocker is “human approval missing”, explain what must be approved and stop at the approval gate.
- Never change readiness, rule, review, or test results merely to force the ticket forward.
- Do not modify `plan.md` directly when the expected workflow requires a plan-review or plan-fix artifact.
- Do not overwrite user changes or resolve merge conflicts automatically unless an explicit safe policy permits it.
- Show the proposed recovery actions before execution.
- Record diagnostics, confirmation, mutations, retries, and results in the audit trail.
- Prevent concurrent recovery sessions for the same ticket.
- Enforce a retry and iteration limit so the agent cannot enter an infinite fix loop.
- Stop and request user input when recovery would require a product decision or destructive operation.

## Automatic bug issue creation

When Claude identifies a reproducible bug in AI Dev Factory rather than a ticket-specific failure, it must create a deduplicated GitHub issue containing:

- concise title;
- affected pipeline stage;
- ticket and project identifiers;
- expected behavior;
- actual behavior;
- sanitized error message and relevant logs;
- reproduction steps;
- suspected component;
- recovery workaround, when available;
- links to related existing issues;
- originating recovery session identifier.

Before creating the issue, search open issues for an equivalent bug. If one exists, link it in the recovery report instead of creating a duplicate.

Secrets, credentials, private prompts, unrestricted logs, and sensitive local paths must not be included in the issue.

## UX requirements

- Add a suggested or explicit `Unblock ticket` action in the AI Workspace when the active ticket is blocked.
- Display live recovery stages:
  - `DIAGNOSING`
  - `PLAN_READY`
  - `AWAITING_CONFIRMATION`
  - `APPLYING_FIX`
  - `RETRYING_STAGE`
  - `VERIFYING`
  - `RECOVERED`
  - `NEEDS_USER_INPUT`
  - `BUG_REPORTED`
  - `FAILED`
- Show the detected root cause and the exact recovery operations before confirmation.
- Stream concise progress and relevant sanitized log excerpts.
- On success, show the new ticket state and next pipeline stage.
- On partial recovery, clearly state what remains blocked and what the user must do.
- When an issue is created or linked, show its URL in the conversation.

## Acceptance criteria

- “Unblock this ticket” resolves the active Workspace ticket without requiring its identifier to be repeated.
- Claude diagnoses the actual blocking stage using current pipeline state and artifacts.
- A clear root cause and recovery plan are shown before any mutation.
- The Supervisor executes only allowlisted, ticket-scoped recovery operations.
- Human approval gates are never bypassed or fabricated.
- A recoverable missing/malformed artifact can be repaired using the correct repository convention.
- A transient failed stage can be retried and its new result verified.
- The action verifies that the ticket moved to the expected next state before reporting success.
- Recovery stops after the configured retry/iteration limit.
- A reproducible platform bug results in a deduplicated, sanitized GitHub issue or a link to an existing equivalent issue.
- The final chat response includes diagnostics, actions performed, retry result, final ticket state, and any bug issue URL.
- Existing manual recovery controls continue to work.

## Out of scope

- Bypassing human review or approval.
- Silently changing business requirements or acceptance criteria.
- Unrestricted autonomous shell access.
- Destructive Git operations.
- Automatic resolution of ambiguous merge conflicts.
- Recovery across unrelated projects or tickets.
