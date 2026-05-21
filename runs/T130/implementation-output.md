All three fixes are in place. Here's a summary of the changes made:

**Files modified:**

1. **`tools/agent_runner/run_analysis.py`** (lines 183-203) — **Blocking fix**: replaced `startswith(".ai-dev-factory/")` string check with a resolve-based check (`(project_root / rel_path).resolve()` vs `str(project_root) + "/"`). This closes the `.ai-dev-factory/../../../etc/passwd` bypass where the old prefix check passed but the resolved path escaped the project root. Also added a post-write `yaml.safe_load` validation of `deploy.yml` (recommended fix).

2. **`tests/test_run_analysis.py`** — Updated `test_main_path_traversal_rejected` assertion to match the new error message (`"escaping project root"`), and added `test_main_path_traversal_with_prefix_bypass_rejected` (9th test) that specifically covers the `.ai-dev-factory/../../../etc/passwd` bypass case that the old check missed.

3. **`services/control_api/services/analysis_manager.py`** (line 67) — **Optional fix**: `get_analysis_status` now catches `httpx.ConnectError` separately and returns `AnalysisStatus(state="failed", error="supervisor_unreachable")` instead of silently returning `idle`.
