# Plan review — T198 dependency source and status normalization

The T198 plan is broadly aligned with the issue goal: it introduces an advisory Ticket Readiness Evaluator, persists readiness metadata, exposes API/UI, and explicitly avoids scheduler or worker-dispatch changes.

However, two points should be corrected before implementation starts.

## Blocking issue 1 — fragile dependency merge detection

The current plan allows dependency checks using:

```text
git log --grep "T<ID>" main
```

This is fragile because merge commit messages are not a reliable source of truth:

- squash merges may change the commit message
- PR titles may not contain the ticket ID consistently
- ticket IDs can appear in unrelated commits
- rebases or manual merges may not preserve the expected grep pattern
- future multi-project support needs a structured source of truth

The evaluator should prefer structured runtime data when available.

Preferred dependency resolution order:

1. Existing runtime DB ticket/run/PR metadata, if it already stores merge state or PR state.
2. Existing GitHub/PR metadata helpers, if available in the project.
3. Local Git inspection as a fallback only, not as the primary strategy.

If no reliable merge-state source exists yet, the plan should make this explicit and introduce a small helper abstraction so the implementation can be replaced later without changing evaluator logic.

Suggested helper:

```text
is_ticket_merged(project_root, ticket_id) -> MergeCheckResult
```

with result fields:

```text
status: merged | not_merged | unknown
source: runtime_db | github_metadata | git_fallback | unknown
reason: string
```

Unknown should block readiness by default, with a clear reason.

## Blocking issue 2 — status naming must be normalized

The issue describes user-facing states:

```text
READY_CANDIDATE
BLOCKED
```

The plan stores lowercase/internal values:

```text
ready_candidate
blocked
```

That is acceptable only if the plan clearly defines canonical internal values and UI/API mapping.

Required clarification:

- DB/internal enum values should be lowercase snake_case:

```text
not_started
queued
running
ready_candidate
blocked
failed
```

- API may expose the same canonical values, or expose labels separately.
- UI labels should render uppercase/human-readable labels:

```text
READY CANDIDATE
BLOCKED
```

Avoid mixing enum styles in logic and tests.

## Required correction

Update `runs/T198/plan.md` so that:

1. Dependency merge detection uses a structured helper instead of directly relying on `git log --grep`.
2. Git log grep is only a fallback.
3. Unknown dependency merge state blocks readiness with a clear reason.
4. Status enum canonical values are explicitly defined as lowercase snake_case.
5. UI/API label mapping is explicitly described.

## Review verdict

PLAN_FIX_REQUIRED until dependency merge detection and readiness status normalization are clarified.
