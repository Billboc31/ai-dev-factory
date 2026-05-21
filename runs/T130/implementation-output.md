All 20 tests pass. Here's what was done:

**Fix 1 — Path traversal (`run_analysis.py:183-193`):** Added a guard that raises `RuntimeError` for any LLM-generated path not starting with `.ai-dev-factory/`, preventing writes outside that directory.

**Fix 2 — New test file (`tests/test_run_analysis.py`, 8 tests):**

| Test | Covers |
|------|--------|
| `test_extract_files_valid_response` | Well-formed 3-file LLM output → correct dict |
| `test_extract_files_empty_output` | No blocks → empty dict |
| `test_extract_files_malformed_delimiter` | Broken delimiter → empty dict |
| `test_extract_files_partial_block` | Unclosed block → empty dict |
| `test_main_happy_path_writes_files_and_state` | Full orchestration: files written, state=success, branch/PR captured |
| `test_main_missing_required_file_sets_failed_state` | Missing deploy.yml → state=failed, error references deploy.yml |
| `test_main_path_traversal_rejected` | `../../etc/passwd` path → state=failed, no file written |
| `test_main_llm_failure_sets_failed_state` | LLM subprocess error → state=failed |
