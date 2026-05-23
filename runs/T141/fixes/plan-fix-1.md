# Plan fix — T141 V1

## New objective

Implement safe sandbox lifecycle management for existing sandbox environments.

The primary user need is:

- start sandbox
- stop sandbox
- restart sandbox
- cleanup/delete sandbox
- refresh sandbox state

The implementation should focus on stable runtime lifecycle behavior before introducing generic topology abstractions.

---

# Included

## Sandbox lifecycle operations

Implement:

- stop sandbox
- restart sandbox
- cleanup/delete sandbox
- refresh sandbox state

## Safe shutdown behavior

Stopping a sandbox must:

- stop docker compose services for the sandbox
- stop sandbox supervisor if running
- stop sandbox daemon/workers if running
- release allocated ports
- remove stale locks and pid files
- preserve sandbox state consistency

The main runtime must never be impacted.

## Cleanup behavior

Deleting a sandbox must:

- stop the sandbox first if still running
- remove sandbox runtime artifacts safely
- remove sandbox worktree safely
- remove compose resources associated with the sandbox

Optional:

- preserve logs/state artifacts before deletion

## Lifecycle API endpoints

Add minimal lifecycle endpoints:

- POST /sandboxes/{id}/stop
- POST /sandboxes/{id}/restart
- POST /sandboxes/{id}/refresh
- DELETE /sandboxes/{id}

## Dashboard integration

Expose:

- running/stopped state
- ports
- runtime root
- uptime if available

Add lifecycle actions in the dashboard:

- stop
- restart
- refresh
- delete

## Tests

Add tests for:

- stop lifecycle
- restart lifecycle
- cleanup/delete
- port release
- stale lock cleanup
- concurrent sandbox safety

---

# Excluded

Do NOT implement in this ticket:

- generic runtime topology model
- sandbox-profile.yml
- component DAG/orchestration
- component health polling
- generic component abstractions
- distributed orchestration
- Kubernetes/cloud support
- AI auto-healing loops

These should be handled in later dedicated tickets.

---

# Acceptance criteria

- sandbox can be stopped safely
- sandbox can be restarted safely
- sandbox can be deleted safely
- ports are released correctly after stop/delete
- stale locks and pid files are cleaned safely
- dashboard lifecycle actions work
- main runtime is never affected
- concurrent sandboxes remain isolated
