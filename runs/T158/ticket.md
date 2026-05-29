# T158 — T158 - Add named environments with configurable Traefik URLs

**Source**: GitHub Issue #165

## Description

# T158 - Add named environments with configurable Traefik URLs

## Goal

Introduce a proper “Environments” workflow distinct from the Deployer tab.

The Environment system should allow users to create named environments with custom Traefik URLs, branch selection, runtime metadata and lifecycle actions, while keeping the Deployer focused on fast validation/testing deployments.

---

## Product positioning

### Deployer

Purpose:

```text
quick validation deployment
```

Typical usage:

- test a branch quickly
- validate build/runtime
- smoke test
- temporary deploy
- convergence/debugging workflow

The deployer is NOT intended to manage long-lived environments.

---

### Environments

Purpose:

```text
named deployable environments
```

Typical usage:

- demo environments
- QA environments
- shared local URLs
- stable branch deployments
- persistent development/testing instances

Environments are user-managed runtime entities.

---

## UX goals

The Environments tab should feel like:

```text
simple local platform environment management
```

NOT:

- raw Docker management
- port management UI
- low-level runtime debugging

The UI should emphasize:

- pretty URLs
- environment identity
- deployed ref
- status visibility
- easy open/redeploy/delete flows

---

# Included

## Backend — environment metadata model

Add environment metadata persistence:

```text
environment_id
name
project_id
branch/ref
web_host
api_host
created_at
updated_at
last_deployed_at
persistent
auto_cleanup_policy
sandbox_id
status
```

Environment metadata may initially live in SQLite runtime storage.

---

## Backend — deploy environment API

Add environment-oriented deployment flow:

```text
POST /projects/{id}/environments
```

Request example:

```json
{
  "name": "demo-client",
  "branch": "ticket/T157-...",
  "web_host": "demo-client.ai-dev-factory.localhost",
  "api_host": "api.demo-client.ai-dev-factory.localhost",
  "persistent": true
}
```

Behavior:

- validate branch/ref
- validate host uniqueness
- validate DNS-safe hostnames
- create sandbox environment
- configure Traefik routes using provided hosts
- persist environment metadata
- return URLs and runtime metadata

---

## Backend — Traefik host validation

Add validation rules:

- host must be unique
- host cannot collide with existing runtime routes
- host must be DNS-safe
- reserved/internal hosts forbidden
- reject invalid localhost wildcard formats

Errors must be explicit and user-readable.

---

## Backend — environment lifecycle endpoints

Add actions:

```text
redeploy environment
stop environment
delete environment
refresh status
```

Deleting an environment must:

- remove proxy routes
- cleanup sandbox
- cleanup metadata
- cleanup runtime artifacts safely

---

## Frontend — Environments tab redesign

Replace the current low-level environment view with a proper environment dashboard.

### Create Environment modal

Fields:

- Environment name
- Project
- Branch/ref
- Web URL host
- API URL host
- Persistent toggle
- Auto-cleanup policy
- Optional description

Behavior:

- auto-generate hosts from environment name
- allow manual override
- show live validation errors
- preview final URLs before deploy

---

## Frontend — Environment cards

Each environment card should display:

### Primary information

- environment name
- pretty Web URL
- pretty API URL
- deployed branch/ref
- commit SHA
- runtime status

### Status indicators

- proxy ready
- healthcheck status
- smoke status
- failing step when available

### Runtime metadata

- sandbox id
- compose project
- created_at
- last deployed
- runtime root

### Actions

- Open Web
- Open API
- Copy URLs
- Redeploy
- Refresh
- View logs
- Stop
- Delete

---

## Frontend — URL UX requirements

Pretty URLs must be the primary UI element.

Fallback localhost ports:

- hidden by default
- collapsible debug section only

Users should never need to manually inspect ports during normal usage.

---

# Excluded

- No Kubernetes support
- No cloud deployment support
- No authentication/multi-user access control
- No SSL certificate automation
- No wildcard DNS management beyond localhost/dev routing
- No production deployment workflows
- No environment cloning yet
- No automatic scaling/orchestration
- No convergence auto-fix loop changes

---

# Acceptance criteria

- Users can create a named environment from the UI
- Users can choose custom Traefik web/API hosts
- Host collisions are detected and rejected
- Environment URLs become reachable through Traefik
- Environment cards clearly expose URLs and runtime status
- Users can redeploy/update an environment
- Users can stop/delete an environment cleanly
- Runtime dashboard and environment dashboard remain distinct responsibilities
- Deployer tab still works unchanged for quick validation deployments
