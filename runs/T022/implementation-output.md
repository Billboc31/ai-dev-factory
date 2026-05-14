Implementation complete. Here's a summary of what was done:

**`tools/agent_runner/run_step.py`** — 3 targeted changes:
- `prompt_candidates()`: appends `prompts/generic/{step}.md` as the last fallback candidate
- `find_prompt()`: now returns `tuple[Path, str]` — logs resolved source (`ticket-specific` or `generic`) to `runtime.log`
- `main()`: unpacks the tuple; when source is `generic`, reads `runs/TXXX/ticket.md` and appends its content to the prompt (raises `RunnerError` with an explicit message if `ticket.md` is absent); `show_next()` updated to unpack with `_`

**`prompts/generic/`** — 5 new files: `planner.md`, `coder.md`, `review.md`, `tester.md`, `memory-updater.md`

**`tests/test_prompt_resolution.py`** — 6 tests covering: ticket-specific priority, generic fallback, error on no prompt, source logging, ticket.md injection, and error on missing ticket.md
