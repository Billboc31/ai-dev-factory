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

## Fix loop

When `--auto` transitions into `PLAN_FIX_REQUIRED` or `IMPLEMENTATION_FIX_REQUIRED`, the runner
automatically enriches the next step's prompt with the previous output, the review, and the fix
instructions before passing it to the external command.

### Naming conventions

**Review files** — placed in `runs/TXXX/reviews/`:
- Plan reviews: `plan-review.md` (stable) or `plan-review-vN.md` (versioned)
- Implementation reviews: `implementation-review.md` (stable) or `implementation-review-vN.md` (versioned)

**Fix instruction files** — placed in `runs/TXXX/fixes/`:
- Plan fixes: `fixes/plan-fix-N.md` or `fixes/plan-fix-<slug>.md`
- Implementation fixes: `fixes/implementation-fix-N.md`

**Selection rule**: the runner always picks the file with the latest mtime. This covers both stable
(single overwritten file) and versioned (new file each round) naming strategies.

**Generated files** — `fixes/context-*.md` files are written by the runner and must never be
created or edited manually. They are excluded from artifact selection to avoid recursive injection.

### Workflow

1. After each review that produces `*_FIX_REQUIRED`, create the fix instruction file:
   ```
   runs/TXXX/fixes/plan-fix-1.md          # plan fix
   runs/TXXX/fixes/implementation-fix-1.md # implementation fix
   ```
2. Relaunch auto:
   ```bash
   python tools/agent_runner/run_ticket.py TXXX --auto --exec-cmd "claude --dangerously-skip-permissions -p"
   ```
3. The runner logs the injected artifacts and creates a timestamped context file.

### Example `runtime.log` output after a fix loop

```
[2026-05-08T12:00:00Z] auto-run start: state=PLAN_FIX_REQUIRED
[2026-05-08T12:00:00Z] auto-run: running step=planner
[2026-05-08T12:00:00Z] auto-run: fix context: previous_output=runs/TXXX/plan.md
[2026-05-08T12:00:00Z] auto-run: fix context: review=runs/TXXX/reviews/plan-review.md
[2026-05-08T12:00:00Z] auto-run: fix context: fix_instructions=runs/TXXX/fixes/plan-fix-1.md
[2026-05-08T12:00:00Z] auto-run: fix context: context_file=runs/TXXX/fixes/context-20260508T120000Z.md
[2026-05-08T12:00:01Z] auto-run: step=planner done rc=0
[2026-05-08T12:00:01Z] auto-run: transition PLAN_FIX_REQUIRED → PLAN_REVIEW_NEEDED
```
