40/40 passing in under 1 second (properly isolated now, no sandbox process spawning). The two fixes were:

1. `sandbox_manager.py` — added `proxy_routes_dir` param to `SandboxManager.__init__` so tests can inject an isolated routes directory
2. `environments.py` — collision check now uses `mgr._proxy.routes_dir` (the proxy manager's actual directory) instead of the hardcoded global `resolve_proxy_routes_dir()`, making validation consistent with what gets written
3. `tests/test_environment_routes.py` — `_make_app()` now passes `proxy_routes_dir=tmp_path / "proxy_routes"` so each test gets a clean routes directory
