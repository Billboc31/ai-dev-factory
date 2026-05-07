All three fixes are applied correctly:

1. **Défaut 1 (bloquant)** — `run_ticket.py:346-349`: if `rc != 0` after `_call_run_step`, we now print an error, log it, and return exit code 2 — state is never advanced.

2. **Défaut 2** — `run_ticket.py:190`: `path.with_suffix(".json.tmp")` replaced with `path.parent / (path.name + ".tmp")`, safe across all Python versions.

3. **Défaut 3** — `README.md`: the runtime.log bullet now mentions `tail -f runs/TXXX/runtime.log` as the monitoring mechanism for long steps.
