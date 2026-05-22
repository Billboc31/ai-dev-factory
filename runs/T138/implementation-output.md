All 26 tests in the auto-fix test files pass. The 45 failing tests are pre-existing failures in unrelated files.

Here's a summary of the three fixes applied:

**[BLOQUANT] `auto_fix_loop.py`** — Removed `_REQUIRED_SCRIPTS = [...]`. `run_scripts_validation` now discovers scripts dynamically via `sorted(scripts_dir.glob("*.sh"))`. A missing or empty scripts directory returns success (nothing to validate), which is correct for generic projects. Tests updated: `_make_scripts` no longer references `afl._REQUIRED_SCRIPTS`, test 4 replaced by two new tests (`test_run_scripts_validation_empty_scripts_dir_is_success` and `test_run_scripts_validation_missing_scripts_dir_is_success`).

**[MINEUR] `main.py` proposal status** — Replaced the binary `rejected/ready` with three-way logic: `ready` (all valid), `ready_with_warnings` (some valid, some invalid), `rejected` (all invalid).

**[MINEUR] `main.py` `max_retries` validation** — Added `Field` import from pydantic and constrained `max_retries: int = Field(default=3, ge=1, le=50)`.
