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
- exposes a minimal workflow state machine
- supports controlled external command execution
- provides a sequential ticket runner

## Usage

### Show a canonical prompt

```bash
python tools/agent_runner/run_step.py T002 planner --show-prompt
```

### Show the next workflow step

```bash
python tools/agent_runner/run_step.py T002 --next
```

### Execute a single step through the sequential runner

```bash
python tools/agent_runner/run_ticket.py T002 \
  --once planner \
  --exec-cmd "claude"
```

### Execute a direct external command

```bash
python tools/agent_runner/run_step.py T002 planner \
  --exec-cmd "claude"
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
