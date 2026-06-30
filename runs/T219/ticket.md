# T219 — Add Backlog Batch dashboard with dependency graph visualization

**Source**: GitHub Issue #294

## Description

# Context

The new batch-based backlog ingestion workflow introduces backlog batches, global dependency analysis, and Dispatcher-driven execution.

As the number of tickets grows, understanding what is currently executing, what is blocked, and what will execute next becomes difficult.

We need a dedicated UI to visualize batches, dependency analysis results, and Dispatcher execution state.

# Goal

Create a new Dispatcher dashboard section dedicated to backlog batches and dependency visualization.

The dashboard should provide a complete view of:

- current executing batch
- next collecting batch
- dependency analysis results
- Dispatcher execution status
- ticket dependency graph

# New page

```text
/dispatcher/batches
```

# MVP Features

## 1. Batch list view

Display all batches in a table.

Columns:

```text
Batch ID
Status
Ticket count
Created at
Last activity
Progress
Current phase
```

Statuses:

```text
collecting
frozen
dependency_analysis_running
dependency_analysis_failed
readiness_running
dispatching
completed
```

Actions:

```text
Open details
Force freeze
Retry dependency analysis
Recompute dependencies
Cancel batch
```

# 2. Batch detail page

Display detailed information for a selected batch.

Example:

```text
Batch B001
Status: Dispatching

Created: ...
Frozen: ...
Dependency Analysis: Completed
Readiness: Completed
```

Display all tickets with:

```text
Ticket ID
Title
Status
Execution phase
Dependencies
Readiness state
Dispatcher state
```

# 3. Current and next batch overview

Display:

```text
Current batch
Next batch
```

Example:

```text
Current batch: B001 (dispatching)
Next batch: B002 (collecting)
```

This gives operators immediate visibility into upcoming work.

# 4. Dependency graph visualization

Provide a visual graph of ticket dependencies.

Recommended library:

```text
React Flow
```

Each ticket is represented as a node.

Relationships are displayed as edges.

Example:

```text
T001
└── T010
    ├── T011
    ├── T012
    │    └── T016
    └── T013
         └── T015
```

Node colors:

```text
green  = done
blue   = running
gray   = waiting
orange = waiting human
red    = failed
purple = selected by Dispatcher
```

# 5. Execution phase visualization

Provide a phase-oriented view generated from dependency analysis.

Example:

```text
Phase 1
- T001

Phase 2
- T010

Phase 3 (parallel)
- T011
- T012
- T013
```

# 6. Dispatcher insights

Display:

```text
Runnable tickets
Blocked tickets
Blocking reasons
Conflicting tickets
```

Examples:

```text
T015 blocked by T011
T020 conflicts with T021
```

# Refresh behavior

The page should auto-refresh periodically.

Recommended default:

```text
10 seconds
```

# Acceptance criteria

- New `/dispatcher/batches` page exists.
- All batches are visible.
- Operators can inspect current and next batches.
- Dependency graph is rendered visually.
- Dispatcher blocking reasons are visible.
- Execution phases are displayed.
- The page auto-refreshes.
- Graph rendering remains usable with dozens of tickets.
- Existing Dispatcher pages continue to work unchanged.
