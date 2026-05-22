All 5 tests pass. Fix applied:

**`services/supervisor/path_mapper.py:18`** — replaced `path.startswith(self.container_root)` with `path == self.container_root or path.startswith(self.container_root + "/")`. This prevents a path like `/applications/foo` from incorrectly matching when `CONTAINER_RUNTIME_ROOT=/app`.

**`tests/test_host_path_mapping.py`** — added `test_ambiguous_prefix_not_mapped` covering exactly this scenario.
