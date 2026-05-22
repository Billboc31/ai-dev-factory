# Plan fix — T139 V1

## New objective

Implement a safe first version of the Runtime Dashboard.

The first version should focus on:
- runtime observability
- sandbox visibility
- proposal visibility
- log access
- limited safe cleanup

Avoid advanced runtime orchestration or destructive cleanup automation in this ticket.

## Included

### Runtime dashboard page

Add a dedicated Runtime Dashboard page.

### Sandbox runs section

Display:
- sandbox id
- project id
- status
- timestamps
- ports
- worktree path
- compose project name

Actions:
- refresh
- open logs
- cleanup completed sandbox only

No rerun or stop actions in this ticket.

### Proposal runs section

Display:
- proposal id
- sandbox id
- status
- changed files count
- timestamps

Actions:
- open proposal summary
- delete completed proposal only

No patch apply or rerun logic.

### Runtime health section

Read-only display:
- supervisor status
- active jobs count
- stale pid files
- stale lock files

No automatic cleanup actions.

### Logs viewer

Add:
- sandbox log viewer
- polling refresh
- stop polling when closed

### Limited cleanup

Allow cleanup only for:
- completed sandboxes
- failed sandboxes
- completed proposals

Cleanup must reject:
- running jobs
- active locks
- main runtime paths

### Generic metadata-driven architecture

No project-specific assumptions.
All rendering must rely on generic runtime metadata.

### Tests

Add tests for:
- sandbox listing
- proposal listing
- cleanup rejection for active jobs
- log retrieval
- runtime health display

## Excluded

- sandbox rerun
- sandbox stop
- global stale cleanup automation
- orphan artifact cleanup
- patch apply
- proposal execution
- automatic merge
- cloud deployment
- tester-agent orchestration

## Acceptance criteria

- Runtime Dashboard page renders correctly
- sandbox runs and proposal runs are visible
- logs are accessible
- runtime health is visible
- cleanup works only for completed or failed artifacts
- active jobs cannot be deleted
- no project-specific assumptions exist
