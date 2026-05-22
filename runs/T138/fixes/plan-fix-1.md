# Plan fix — T138 V1

## New objective

Implement a safe dry-run AI auto-fix proposal workflow.

The system should:

- collect sandbox failure context
- call the configured AI runtime
- generate operational patch proposals
- validate allowed file paths
- expose proposed changes in the dashboard

The system must NOT automatically apply fixes or rerun validation yet.

This ticket intentionally focuses on:

- observability
- patch proposal generation
- safe validation
- generic project support

before introducing automatic execution loops.

---

# Included

## Failure context collection

Collect:

- sandbox state
- failing step
- sandbox logs
- deploy.yml
- operational scripts
- sandbox metadata

No ai-dev-factory-specific assumptions.

## Generic AI integration

Use the configured AI runtime abstraction.

Do NOT hardcode:

- Claude APIs
- specific models
- ai-dev-factory-specific prompts

The AI request must remain generic and runtime-configurable.

## Patch proposal generation

The AI runtime returns:

- proposed file modifications
- target relative paths
- reasoning summary

## Allowed files validation

Restrict modifications to allowed operational artifacts only.

Reject:

- path traversal
- runtime/core modifications
- unrelated project files

## Dashboard proposal UI

Add a dry-run proposal panel showing:

- sandbox id
- failing step
- proposed changed files
- patch preview
- AI reasoning summary
- proposal status

## Persistence

Persist proposal state to disk.

## Tests

Add tests for:

- generic deploy.yml handling
- malformed AI output
- disallowed paths
- patch proposal persistence
- proposal rendering state

---

# Excluded

- automatic patch application
- sandbox reruns
- retry loops
- automatic convergence
- automatic merge
- production deployment
- tester-agent integration
- async orchestration loops

---

# Acceptance criteria

- sandbox failure context can be collected generically
- the configured AI runtime can generate patch proposals
- invalid or dangerous proposals are rejected safely
- proposals are persisted and visible in the dashboard
- no files are automatically modified
- no sandbox reruns occur automatically
- no ai-dev-factory-specific assumptions exist in the workflow
