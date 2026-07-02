# T222 — Add Dependency Analyzer reasoning summary to Batch dashboard

**Source**: GitHub Issue #301

## Description

# Context

The Batch dashboard now displays execution phases, blocked tickets and dependency relationships.

However, when the dependency graph looks unexpected (for example T001 and T010 being considered parallel), there is currently no way to understand *why* the Global Dependency Analyzer reached that conclusion.

This makes it difficult to debug prompts, improve the analyzer, or trust its decisions.

# Goal

Expose the reasoning produced by the Global Dependency Analyzer directly in the Batch dashboard.

The objective is to make every dependency decision explainable.

# MVP

## 1. Batch analysis summary

Add a new collapsible section:

```text
Dependency Analysis Summary
```

Display:

- Overall implementation strategy
- Foundation tickets detected
- Bootstrap tickets detected
- Important inferred dependencies
- Parallel execution opportunities
- Conflicts detected and how they were resolved
- Warnings or assumptions made by the analyzer

## 2. Ticket reasoning

For each ticket, display:

```text
Execution phase
Why this phase?
Dependencies inferred
Reasoning
Confidence (if available)
```

Example:

```text
T010

Phase 4

Reason:
The ticket bootstraps the application after the architectural foundation defined by T001 and the foundational setup completed by T004 and T005.
```

## 3. Raw analyzer output

Provide a collapsible developer section:

```text
Raw Dependency Analyzer Output
```

Display the original structured JSON returned by the analyzer.

This should help debugging prompt quality without inspecting logs.

## 4. Persistence

Persist the analyzer reasoning with the batch so the dashboard can be refreshed without recomputing analysis.

Suggested fields:

- analysis_summary
- ticket_reasoning
- raw_analyzer_output

Exact storage format is implementation-defined.

# Acceptance criteria

- Batch dashboard displays a Dependency Analysis Summary.
- Each ticket exposes an explanation of its assigned phase and inferred dependencies.
- The original analyzer output can be inspected from the UI.
- Refreshing the page does not require rerunning dependency analysis.
- The feature is read-only and does not modify the dependency graph.
- Debugging unexpected dependency decisions no longer requires reading daemon logs.
