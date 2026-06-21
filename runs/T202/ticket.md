# T202 — T202 - Prevent planner from returning artifact summaries instead of artifact content during PLAN_FIX_REQUIRED

**Source**: GitHub Issue #259

## Description

# T202 - Prevent planner from returning artifact summaries instead of artifact content during PLAN_FIX_REQUIRED

## Context

A reproducible failure mode has been observed during the `PLAN_FIX_REQUIRED` workflow.

Instead of rewriting the target artifact (`runs/Txxx/plan.md`), the planner sometimes produces a meta-report describing what was changed.

Example invalid outputs:

```text
The plan has been rewritten...
Key points covered...
The plan now contains...
Plan rewritten as a real implementation document...
```

The generated file therefore becomes a report about the artifact rather than the artifact itself.

This behavior has been reproduced multiple times on T201.

## Problem

Current validation is intentionally permissive to avoid blocking planning unnecessarily.

However, this permissiveness allows outputs that are clearly not implementation artifacts.

We want to improve robustness without reintroducing the overly rigid validation rules that previously caused many false positives.

## Goals

Improve PLAN_FIX_REQUIRED behavior so that planners reliably rewrite the requested artifact instead of returning a compliance report.

The solution should remain tolerant of different writing styles and plan structures.

## Non-goals

Do not:

- enforce a single exact plan template
- require strict ordering of all sections
- require exact wording
- reject plans because of formatting differences
- introduce brittle validation rules

## Suggested approach

### 1. Strengthen planner prompts

When regenerating an artifact after a review:

```text
Your response will be written verbatim to <artifact>.
Rewrite the artifact itself.
Do not describe the modifications.
Do not explain what changed.
Do not produce status reports.
```

### 2. Add lightweight artifact heuristics

Validation should remain permissive but detect obvious meta-reports.

Examples of suspicious openings:

```text
The plan...
This plan...
Plan rewritten...
Key points covered...
The document now...
```

The validator should lower confidence or request another attempt when the whole file appears to be a report rather than an artifact.

### 3. Add artifact-type aware validation

Validators should know the expected artifact type:

```text
plan
review
fix
code
ADR
```

and use soft heuristics appropriate for each type.

### 4. Retry strategy

If a generated artifact is classified as a meta-report:

```text
retry planner once with an explicit artifact-only instruction
```

before failing the ticket.

## Acceptance criteria

- PLAN_FIX_REQUIRED regenerations rewrite the requested artifact in most cases.
- Meta-reports are detected with high precision.
- Validation remains permissive and avoids excessive false positives.
- Existing successful planning workflows continue to work.
- The system supports different writing styles and document structures.
- At least one automated test reproduces and prevents the T201 failure mode.
