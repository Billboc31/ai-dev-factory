Both files compile clean. Here's what was implemented:

**`run_step.py`** — Added `--extra-context-file <path>` flag. When present alongside `--exec-cmd`, reads the file and appends its content to the canonical prompt (separated by `\n\n---\n\n## Contexte de retry injecté par run_ticket.py\n\n`) before sending to the external command. Raises `RunnerError` with a non-zero exit if the file is missing.

**`run_ticket.py`** — Three additions:
- `_collect_fix_artifacts(ticket_id, state)`: selects `previous_output` (fixed path from `DEFAULT_OUTPUTS`), `review` (latest by mtime via glob), and `fix_instructions` (latest by mtime, `context-*` files excluded). Raises `TicketRunnerError` with the expected path if any artifact is absent.
- `_build_fix_context_file(ticket_id, artifacts)`: concatenates the three artifacts with section headers into `runs/TXXX/fixes/context-<ts>.md`.
- `_call_run_step` now accepts `extra_context_file: Path | None = None` and appends `--extra-context-file` when set.
- `auto_run` checks for fix states before calling `_call_run_step`, collects/builds the context file, and logs each artifact path to `runtime.log`.

**`README.md`** — Added a "Fix loop" section documenting naming conventions, selection rules, the `context-*.md` exclusion, the relaunch command, and an example `runtime.log` output.
