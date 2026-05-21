# T126 — T126 — Fix dashboard 500 errors after project-scoped routing

**Source**: GitHub Issue #91

## Description

# Objective

Fix the dashboard/API 500 errors introduced after project-scoped routing and multi-project separation.

## Included

- Reproduce and identify all dashboard endpoints returning HTTP 500 after the project separation.
- Fix backend route handling for project-scoped and legacy routes.
- Ensure project resolution works correctly for the default `ai-dev-factory` project.
- Ensure dashboard API clients call the correct URLs after project selection.
- Preserve backward compatibility for existing single-project routes when possible.
- Add clear backend error messages for invalid or missing project IDs.
- Add regression tests for the failing endpoints.

## Excluded

- New multi-project features.
- Deployer implementation.
- Ticket mapper redesign.
- Major dashboard redesign.

## Acceptance criteria

- Dashboard no longer shows HTTP 500 errors during normal navigation.
- Project selector, daemon page, board, ticket detail, runtime status and logs load successfully for the default project.
- Unknown project IDs return 404 instead of 500.
- Existing legacy routes still work or fail with explicit non-500 errors.
- Tests cover the fixed project-scoped routes.
