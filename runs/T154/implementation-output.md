All `HOST_RUNTIME_ROOT` usages in tests go through `monkeypatch.setenv` — no test touches the real route directory. All acceptance criteria met.

---

**Summary of changes:**

**Modified:**
- `tools/agent_runner/run_sandbox.py` — added `import time`, `import urllib.error`, `import urllib.request`; added `_wait_for_proxy_url()` function (polls sandbox URL up to 15s, returns `True` on any HTTP response, `False` on connection-level failure, logs outcome); wired call between `_register_proxy_route()` and `_run_scripts()`
- `.ai-dev-factory/scripts/healthcheck.sh` — when `SANDBOX_API_URL` is set, probes `http://traefik.ai-dev-factory.localhost` first; if it fails, emits `PROXY_INFRA_FAIL` to stdout before app probes run

**Created:**
- `tests/test_proxy_route_wait.py` — 3 unit tests covering the True/False return paths and the log message
- `tests/test_healthcheck_classification.py` — 1 integration test (marked `@pytest.mark.integration`) verifying `PROXY_INFRA_FAIL` appears in stdout when Traefik is down

All 4 new tests pass; all 128 pre-existing tests continue to pass.
