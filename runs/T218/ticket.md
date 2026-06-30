# T218 — Add batch-based backlog ingestion and dependency analysis pipeline before Dispatcher execution

**Source**: GitHub Issue #292

## Description

# Context

The current workflow continuously polls GitHub issues and immediately runs Ticket Intelligence and Readiness.

This works for isolated tickets but is not ideal for Dispatcher-driven execution because dependencies between newly created tickets may not yet be known.

We want to introduce a batch-oriented backlog ingestion workflow.

# Goal

Create batches of newly discovered tickets.

Tickets in a batch should first receive individual Ticket Intelligence analysis.

Once the backlog has been stable for a configurable amount of time, a global dependency analysis should run on the entire batch.

Only after dependency analysis is complete should Readiness and Dispatcher scheduling occur.

# Proposed workflow

```text
Poll GitHub every X seconds
↓
New ticket discovered
↓
Run Ticket Intelligence only
↓
Store ticket in current collecting batch
↓
No new tickets received for Y minutes
↓
Freeze batch
↓
Run Global Dependency Analysis on the whole batch
↓
Update dependencies on tickets
↓
Run Readiness for all tickets in the batch
↓
Dispatcher computes queue
↓
Daemon executes tickets
```

# Global Dependency Analysis responsibilities

The Global Dependency Analysis agent is responsible for building and maintaining a dependency graph for the entire batch.

The agent must analyze all tickets in the batch together and:

- detect implicit dependencies between tickets
- detect foundation/bootstrap tickets
- detect architectural prerequisites
- detect implementation ordering constraints
- detect tickets that can safely run in parallel
- detect conflicting tickets touching the same scope
- propose or update ticket dependencies

Examples:

```text
T001 - Define architecture
T010 - Bootstrap project

→ T010 depends on T001

T011 - Backend foundation
T012 - Frontend foundation

→ T011 depends on T010
→ T012 depends on T010

T015 - Task CRUD API
T016 - Frontend task client

→ T016 depends on T015
```

The analyzer should classify relationships:

```text
HARD_DEPENDENCY
SOFT_DEPENDENCY
FOUNDATION_DEPENDENCY
PARALLEL_COMPATIBLE
CONFLICTING_SCOPE
```

Outputs produced by the analyzer:

- depends_on[]
- blocks[]
- parallel_group
- conflicting_tickets[]
- execution_phase

The analyzer must also produce a global dependency graph.

Example:

```text
T001
└── T010
    ├── T011
    └── T012
         └── T016
```

The analyzer never directly decides execution order.

```text
Dependency Analyzer
→ builds and updates the graph

Dispatcher
→ computes scheduling and execution order
```

# Additional rule

While a batch is actively being executed by the Dispatcher:

```text
new incoming tickets
→ intelligence only
→ placed into next batch
→ no dependency analysis yet
```

This prevents changing the dependency graph while execution is in progress.

# New concepts

Introduce backlog batches with statuses such as:

```text
collecting
frozen
dependency_analysis_running
readiness_running
dispatching
completed
```

# Configuration

Add configurable settings:

```text
github_poll_interval_seconds
batch_idle_timeout_minutes
max_batch_size
allow_parallel_batches
```

# Acceptance criteria

- New tickets are grouped into batches.
- Ticket Intelligence still runs continuously for newly discovered tickets.
- Global Dependency Analysis only runs once a batch becomes idle.
- Dependencies discovered by the analysis are persisted back onto tickets.
- Readiness starts only after dependency analysis completes.
- Dispatcher only schedules tickets from a finalized batch.
- Tickets arriving while a batch is executing are queued for the next batch.
- Batch lifecycle and status are visible in logs.
- Existing non-dispatcher workflows remain supported.
