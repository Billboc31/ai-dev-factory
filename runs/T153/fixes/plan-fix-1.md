# Plan fix — T153 simplified staged implementation

## Objective

Reduce the implementation scope of T153 to a safe and observable V1.

The goal of V1 is:

```text
healthcheck
→ smoke tests
→ observable validation artifacts
→ optional AI fix suggestion
```

NOT yet:

```text
full autonomous self-healing deployment loop
```

## V1 Scope

### 1. Generic smoke test lifecycle

Add support for:

```text
.ai-dev-factory/scripts/smoke.sh
```

Execution order:

```text
start
→ healthcheck
→ smoke tests
```

Smoke tests must:

- prefer proxy URLs when available
- fallback to direct allocated ports
- return clear exit codes
- stream logs to runtime artifacts

### 2. Persist validation artifacts

Persist:

- healthcheck result
- smoke result
- logs
- runtime URLs
- timestamps

Suggested structure:

```text
runs/<ticket>/validation/
```

### 3. Distinguish health vs smoke

State/UI/logs must clearly show:

```text
HEALTHCHECK_PASSED
SMOKE_FAILED
```

and not collapse everything into a single boolean.

### 4. AI fix proposal only

On smoke-test failure:

- collect logs
- collect deployment artifacts
- optionally ask AI runtime for a fix proposal
- persist proposal/diff
- DO NOT auto-apply yet

This keeps the first implementation safe and observable.

### 5. Cleanup remains automatic

Ephemeral validation environments must still stop and cleanup automatically.

## Explicitly deferred to future ticket

The following should be deferred:

- automatic patch application
- redeploy loop
- progress detection
- failure classifier
- retry orchestration
- convergence engine
- automatic smoke test generation
- tester-agent/UAT flows

## Acceptance criteria

- smoke.sh executes after healthcheck
- health and smoke results are distinct
- validation artifacts are persisted
- AI fix proposal can be generated and stored
- no automatic patch application occurs yet
- cleanup still works
- implementation remains generic and project-agnostic
