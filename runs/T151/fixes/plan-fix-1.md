# Plan fix — T151

## Objective

Refactor T151 so that Environments / Deployments become a higher-level product abstraction built on top of the existing sandbox/runtime infrastructure.

T151 must not introduce a second orchestration pipeline.

## Required changes

### 1. Reuse existing sandbox/runtime lifecycle

Do NOT introduce:

- `run_environment.py`
- a second worker orchestration pipeline
- a second port registry implementation
- a parallel deployment state machine
- a separate deploy execution engine

Instead:

- environments should internally reuse the existing sandbox/runtime lifecycle
- environment lifecycle modes should map to existing sandbox lifecycle modes
- existing supervisor orchestration should remain the execution backend
- existing deploy/undeploy/cleanup logic should remain canonical

## 2. Reposition T151 as UX + abstraction layer

T151 should primarily introduce:

- environment-oriented dashboard UX
- environment metadata abstraction
- branch/ref deployment selection
- persistent environment management
- deployment views and actions

The runtime engine itself should remain shared.

## 3. Reuse existing infrastructure

Reuse existing:

- sandbox manager/runtime manager
- proxy manager
- undeploy lifecycle
- runtime root isolation
- supervisor orchestration
- lifecycle modes
- logs/state files
- port allocation system
- cleanup pipeline

Avoid creating duplicate implementations.

## 4. Environment abstraction

An environment should conceptually become:

- a named runtime deployment
- backed by the existing sandbox/runtime infrastructure
- with additional metadata:
  - branch/ref
  - environment type
  - deployment mode
  - URLs
  - timestamps

## 5. Minimize backend surface expansion

Prefer:

- adapting existing routes
- extending existing runtime state models
- wrapping existing lifecycle APIs

instead of introducing a fully separate backend stack.

## Acceptance update

- only one runtime orchestration pipeline exists in the system
- environments reuse existing sandbox/runtime execution logic
- no duplicate deploy engine is introduced
- dashboard presents environments as a product abstraction over existing runtime infrastructure
- lifecycle behavior remains centralized and consistent
- implementation remains generic and maintainable
