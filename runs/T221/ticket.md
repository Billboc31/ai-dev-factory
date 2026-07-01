# T221 — Make GitHub issue intake near real-time and decouple polling from ticket processing

**Source**: GitHub Issue #299

## Description

# Context

For demos, the current GitHub issue intake feels too slow.

At the moment, the daemon effectively intakes about one ticket every 30 seconds. With a backlog of 10 tickets, this can take several minutes before the system even starts showing useful activity.

This hurts the demo experience and makes AI Dev Factory feel less reactive than it should.

# Problem

GitHub polling, issue intake, and ticket pipeline processing are too tightly coupled.

The polling interval should not limit the throughput of ticket intake.

# Goal

Make issue discovery and intake feel near real-time.

When multiple new GitHub issues are created, the daemon should detect and enqueue/intake them quickly, instead of processing one issue per full daemon cycle.

# Desired behavior

```text
GitHub poll runs every X seconds
↓
finds all new eligible issues
↓
intakes all new tickets quickly
↓
Ticket Intelligence workers process them independently
```

For demo mode, creating 10 issues should result in all 10 appearing in AI Dev Factory within a few seconds, not several minutes.

# Proposed changes

## 1. Decouple GitHub polling from ticket processing

Separate these concepts:

```text
GitHub polling interval
Ticket intake throughput
Ticket Intelligence concurrency
Readiness concurrency
Dispatcher execution concurrency
```

The GitHub poller should discover all new eligible issues in one pass.

It should not artificially limit intake to one ticket per daemon cycle unless explicitly configured.

## 2. Intake all discovered issues in a batch

When GitHub polling returns multiple eligible issues:

```text
T001
T002
T003
T004
T005
```

all should be registered/intaken quickly.

The pipeline can then schedule intelligence/readiness independently.

## 3. Add configurable settings

Add runtime settings / env overrides for:

```text
GITHUB_POLL_INTERVAL_SECONDS
MAX_ISSUES_INTAKED_PER_POLL
MAX_PARALLEL_TICKET_INTELLIGENCE
MAX_PARALLEL_READINESS
```

Suggested demo-friendly defaults:

```text
GITHUB_POLL_INTERVAL_SECONDS = 5
MAX_ISSUES_INTAKED_PER_POLL = 50
MAX_PARALLEL_TICKET_INTELLIGENCE = 4
MAX_PARALLEL_READINESS = 4
```

Production defaults may remain more conservative if needed.

## 4. Keep execution concurrency separate

This ticket should not make the daemon launch more coding workers than configured.

Intake and intelligence can be fast/parallel, but actual ticket execution remains controlled by Dispatcher/daemon worker limits.

# Acceptance criteria

- GitHub polling can discover and intake multiple issues in a single poll cycle.
- Intake no longer processes only one issue per daemon cycle unless explicitly configured.
- Poll interval is configurable independently from pipeline execution.
- Ticket Intelligence concurrency is configurable independently from GitHub polling.
- Readiness concurrency is configurable independently from GitHub polling.
- Creating 10 eligible issues results in all 10 being registered/intaken within one or two poll cycles.
- Existing daemon execution concurrency limits remain unchanged.
- Logs clearly show how many issues were discovered and intaken per poll.
- Tests cover multiple issues discovered in one poll and verify all are queued/intaken without waiting for 30-second sequential cycles.
