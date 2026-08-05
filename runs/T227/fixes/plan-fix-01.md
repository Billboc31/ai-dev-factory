# Plan fix 01

## Ticket

T227 — Add pull and local backend/frontend redeployment action to AI Workspace

## Source review

`runs/T227/reviews/plan-review-01.md`

## Decision

PLAN_FIX_REQUIRED

## Required plan corrections

### 1. Re-check the repository state at execution time

The dirty-working-tree value collected while the action is proposed is informational only.

After confirmation and immediately before any Git or Docker command, the Supervisor must run `git status --porcelain` again and apply the configured dirty-repository policy to the fresh result.

The regenerated plan must not use a stored `has_dirty` value as the final safety decision.

### 2. Enforce the Supervisor-configured branch

The LLM and frontend must not select an arbitrary executable branch.

For this initial implementation:

- resolve the branch from the project's `default_branch` in `workspace_projects.yml`;
- read the current branch at execution time with `git branch --show-current`;
- refuse execution when the current branch differs from the configured branch;
- use fast-forward-only pull semantics only after the branch check succeeds;
- never merge a requested remote branch into a different current local branch.

The pending action may display the resolved branch but must not treat an LLM-provided or frontend-provided branch as authoritative.

### 3. Avoid blocking the Supervisor during a long deployment

Git pull and Docker builds can take several minutes. Regenerate the plan around a background deployment job that returns immediately with a deployment identifier and a running status.

Define:

- job creation;
- deployment identifier;
- running, succeeded, and failed states;
- status retrieval or polling from the Workspace;
- persisted or safely retained progress;
- final deployed revision;
- preview URL;
- failed stage and sanitized log excerpt.

If synchronous execution is intentionally kept for a limited demo, the plan must explicitly document the limitation and include a design/test proving that other Supervisor requests remain serviceable while deployment runs.

### 4. Strengthen locking and conflict handling

The regenerated plan must:

- use the resolved configured project id as the lock key;
- document that an in-memory lock protects only one Supervisor process/worker;
- release the lock in `finally` after success, command failure, timeout, cancellation, or unexpected exception;
- return HTTP `409 Conflict` when a deployment is already running for the project, not HTTP 500.

### 5. Resolve all sensitive execution values from current Supervisor configuration

At confirmation/execution time, reload `workspace_projects.yml` and resolve from the safe configured `project_id`:

- repository path;
- default/configured branch;
- allowed components;
- Docker Compose service names;
- dirty-repository policy;
- preview URL.

Do not trust or execute paths, branches, service names, commands, or endpoints originating from:

- the frontend;
- the LLM response;
- stale pending-action metadata.

The pending action must contain only safe identifiers and approved business parameters. The frontend confirmation card may display a safe repository identifier, not necessarily the full sensitive host path.

### 6. Complete backend and frontend test coverage

Add backend tests for:

- repository becoming dirty between proposal and confirmation;
- current branch differing from the configured branch;
- rejection of an unapproved branch;
- missing repository path;
- configured path that is not a Git repository;
- Git timeout;
- Docker Compose timeout;
- lock release after command failure, timeout, and unexpected exception;
- first-component failure preventing later components from starting;
- concurrent deployment returning HTTP 409;
- configuration being reloaded at execution;
- stale or tampered paths and service values being ignored.

Add frontend tests for:

- rendering project, safe repository identifier, configured branch, pull flag, components, and dirty warning;
- not displaying the full host path when a safe identifier exists;
- Confirm submitting only the pending `action_id`;
- no executable path, command, branch, or service override being submitted from editable client data.

## Requirements that must remain preserved

- No Git or Docker command runs before explicit confirmation.
- Commands are constructed only by trusted Supervisor code.
- Components remain limited to configured backend/frontend recipes.
- The operation remains local; production/cloud deployment is out of scope.
- Existing Workspace capabilities and informational chat behavior remain unchanged.
- Functional development continues through GitHub issues and the AI Dev Factory pipeline.

## Expected output

Regenerate `runs/T227/plan.md` to incorporate every correction above. Do not implement application code during the plan-fix step.
