# Plan fix — use reliable dependency merge checks and normalize readiness statuses

## Required plan update

Update `runs/T198/plan.md` before starting implementation.

The plan is directionally correct, but it must be corrected in two areas:

1. Dependency merge detection must not primarily rely on commit-message grep.
2. Readiness status values must be normalized and consistently mapped to UI labels.

## 1. Dependency merge detection

Replace direct dependency validation text like:

```text
use git log --grep "T<ID>" main
```

with a helper-based approach:

```text
is_ticket_merged(project_root, ticket_id) -> MergeCheckResult
```

Suggested result:

```json
{
  "status": "merged",
  "source": "runtime_db",
  "reason": "Ticket T001 has a merged PR recorded in runtime DB"
}
```

Supported statuses:

```text
merged
not_merged
unknown
```

Supported sources:

```text
runtime_db
github_metadata
git_fallback
unknown
```

Preferred source order:

1. Runtime DB ticket/run/PR metadata if available.
2. Existing GitHub/PR metadata helpers if available.
3. Local Git inspection fallback.

`git log --grep` may exist only as a fallback and should not be the first-choice mechanism.

If the merge state is `unknown`, readiness must be blocked by default.

Example blocking reason:

```text
Dependency T001 merge state unknown
```

This is safer than accidentally allowing a dependent ticket to run.

## 2. Status normalization

Define canonical internal readiness status values:

```text
not_started
queued
running
ready_candidate
blocked
failed
```

These values should be used in:

- database rows
- backend logic
- API responses
- tests

The UI can render user-facing labels separately:

```text
ready_candidate -> READY CANDIDATE
blocked -> BLOCKED
queued -> QUEUED
running -> RUNNING
failed -> FAILED
not_started -> NOT STARTED
```

Do not mix uppercase enum values with lowercase internal values in backend logic.

## 3. API behavior

`GET /tickets/{ticket_id}/readiness` should return canonical status values.

Example:

```json
{
  "ticket_id": "T198",
  "readiness_status": "blocked",
  "ready_candidate": false,
  "blocking_reasons": [
    "Dependency T197 merge state unknown"
  ]
}
```

The dashboard is responsible for formatting the label.

## 4. Acceptance criteria additions

Add these acceptance criteria to the plan:

- Dependency merge checks use a helper abstraction instead of direct `git log --grep` calls in evaluator logic.
- Runtime DB / structured metadata is preferred over local Git commit-message inspection.
- Unknown dependency merge state blocks readiness with a clear blocking reason.
- Readiness status values are canonical lowercase snake_case internally and in API responses.
- UI renders human-readable labels from canonical status values.

## Non-goals reminder

This fix still must not change:

- scheduler behavior
- worker dispatch
- daemon state machine
- execution queue ordering
- `READY_TO_TAKE` transitions
