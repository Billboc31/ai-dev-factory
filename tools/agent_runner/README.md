# agent_runner

Minimal local executor for ai-dev-factory workflows.

## Goals

The runner is intentionally simple.

It does not:
- call any LLM API
- generate prompts
- merge pull requests
- make autonomous decisions

It only:
- resolves canonical prompts from `prompts/`
- creates `runs/TXXX/`
- stores execution artifacts
- maintains a minimal workflow status file

## Usage

### Show a canonical prompt

```bash
python tools/agent_runner/run_step.py T002 planner --show-prompt
```

### Write a planner output

```bash
python tools/agent_runner/run_step.py T002 planner --write-output < /tmp/plan.md
```

### Write a review artifact

```bash
python tools/agent_runner/run_step.py T002 review --write-output runs/T002/reviews/review.md < /tmp/review.md
```

### Update workflow status

```bash
python tools/agent_runner/run_step.py T002 review --set-status IMPLEMENTATION_APPROVED
```

## Standard run tree

```text
runs/TXXX/
  plan.md
  workflow-status.md
  prompts/
  reviews/
  fixes/
  tests/
  memory/
```

## Prompt resolution

Canonical prompts are resolved from `prompts/TXXX-*.md`.

Examples:
- `prompts/T002-planner.md`
- `prompts/T002-coder.md`
- `prompts/T002-review.md`
- `prompts/T002-tester.md`

The runner never modifies canonical prompts.
