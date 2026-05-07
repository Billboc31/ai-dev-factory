# ai-dev-factory

AI development workflow bootstrap and agent orchestration toolkit.

## `--auto` mode

`--auto` executes one workflow step at a time, driven by `runs/TXXX/state.json` as the canonical state source. Each invocation advances the workflow by exactly one step. There is no automatic merge, no PR creation, and no background loop.

### Prerequisites

The ticket branch must already exist. If not, create it first:

```bash
python tools/agent_runner/run_ticket.py TXXX --branch --branch-slug <slug>
```

### Initialize state (once per ticket)

```bash
python tools/agent_runner/run_ticket.py TXXX --auto-init --branch-slug <slug>
```

- Creates `runs/TXXX/state.json` with `"state": "INIT"`.
- Fails with exit code 2 if `state.json` already exists.
- Fails with exit code 2 if the current branch does not match `ticket/TXXX-<slug>`.

### Execute the next step

```bash
python tools/agent_runner/run_ticket.py TXXX --auto --exec-cmd "claude --print --model claude-opus-4-7"
```

- Reads `state.json` to determine which step to run next.
- Runs the step by invoking `run_step.py` with `--exec-cmd`.
- For review steps, scans the output for an exact keyword on its own line (e.g. `PLAN_APPROVED`).
- Writes the updated state back to `state.json` atomically.
- Appends a timestamped entry to `runs/TXXX/workflow-status.md` (journal only — never read to decide state).
- Logs each action to `runs/TXXX/runtime.log`. To monitor progress during a long step: `tail -f runs/TXXX/runtime.log`.

### Pre-flight gates (checked before every step)

| Gate | Failure exit code |
|---|---|
| `state.json` missing | 2 |
| `state.json` corrupted or unknown state | 2 |
| State is `TEST_COMPLETE` (terminal) | 0 — prints "workflow complete" |
| Current git branch does not match `state["branch"]` | 2 |
| Working tree is not clean | 2 |
| `--exec-cmd` not provided | 2 |
| No review keyword found in step output | 1 — state unchanged |

### State machine

```
INIT
  └─ planner ──→ PLAN_REVIEW_NEEDED
                   ├─ review (PLAN_APPROVED)      ──→ PLAN_APPROVED
                   └─ review (PLAN_FIX_REQUIRED)  ──→ PLAN_FIX_REQUIRED
                        └─ planner ──→ PLAN_REVIEW_NEEDED

PLAN_APPROVED
  └─ coder ──→ IMPLEMENTATION_REVIEW_NEEDED
                 ├─ review (IMPLEMENTATION_APPROVED)      ──→ IMPLEMENTATION_APPROVED
                 └─ review (IMPLEMENTATION_FIX_REQUIRED)  ──→ IMPLEMENTATION_FIX_REQUIRED
                      └─ coder ──→ IMPLEMENTATION_REVIEW_NEEDED

IMPLEMENTATION_APPROVED
  └─ tester ──→ TEST_COMPLETE  (terminal — no automatic merge)
```

### Complete session example

```bash
# Initialize
python tools/agent_runner/run_ticket.py T009 --auto-init --branch-slug my-feature

# Step 1: INIT → PLAN_REVIEW_NEEDED  (runs planner)
python tools/agent_runner/run_ticket.py T009 --auto --exec-cmd "claude --print"
# After each step, commit artifacts before the next --auto
python tools/agent_runner/run_ticket.py T009 --commit

# Step 2: PLAN_REVIEW_NEEDED → PLAN_APPROVED  (runs review, keyword: PLAN_APPROVED)
python tools/agent_runner/run_ticket.py T009 --auto --exec-cmd "claude --print"
python tools/agent_runner/run_ticket.py T009 --commit

# Step 3: PLAN_APPROVED → IMPLEMENTATION_REVIEW_NEEDED  (runs coder)
python tools/agent_runner/run_ticket.py T009 --auto --exec-cmd "claude --print"
python tools/agent_runner/run_ticket.py T009 --commit

# Step 4: IMPLEMENTATION_REVIEW_NEEDED → IMPLEMENTATION_APPROVED  (runs review)
python tools/agent_runner/run_ticket.py T009 --auto --exec-cmd "claude --print"
python tools/agent_runner/run_ticket.py T009 --commit

# Step 5: IMPLEMENTATION_APPROVED → TEST_COMPLETE  (runs tester)
python tools/agent_runner/run_ticket.py T009 --auto --exec-cmd "claude --print"
python tools/agent_runner/run_ticket.py T009 --commit

# Step 6: TEST_COMPLETE → prints "workflow complete — no automatic merge", exit 0
python tools/agent_runner/run_ticket.py T009 --auto --exec-cmd "claude --print"
```

### Invariants

- `state.json` is the only source of truth for workflow state.
- `workflow-status.md` is a human-readable append-only journal; `--auto` never reads it.
- One step per invocation — re-invoke manually to advance.
- No automatic merge, no PR creation, no background loop.
- Any blocking gate returns a non-zero exit code.
