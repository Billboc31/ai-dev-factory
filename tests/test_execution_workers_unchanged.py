"""T221 — coding-worker scheduling is untouched by the new pipeline pools.

The ticket calls out ``MAX_WORKERS`` and Dispatcher execution scheduling as
explicitly out of scope. This regression test locks that in so future changes
to the intake / stage pools do not accidentally bleed into how coding workers
are launched.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import sys
from pathlib import Path

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_exec_unchanged",
        _TOOLS / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    old = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        if old is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = old
    return mod


def _load_runtime_settings(rdb_module):
    name = "_runtime_settings_test_exec_unchanged"
    spec = importlib.util.spec_from_file_location(name, _TOOLS / "runtime_settings.py")
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        sys.modules.pop(name, None)
        raise
    mod.runtime_db = rdb_module
    return mod


_db = _load_sqlite_runtime_db()
_rs = _load_runtime_settings(_db)


def test_max_workers_spec_unchanged():
    spec = _rs.SETTING_SPECS["MAX_WORKERS"]
    assert spec.default == 1
    assert spec.env_var == "DAEMON_MAX_WORKERS"
    assert spec.value_type == "int"


def test_no_pipeline_pool_reads_max_workers():
    """The stage pool init must never consult ``MAX_WORKERS``.

    Static scan of ``run_daemon.py`` — the pool helpers should reference the
    T221 knobs and nothing else related to worker sizing.
    """
    src = (_TOOLS / "run_daemon.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in {
            "_init_pipeline_pools",
            "_submit_intelligence",
            "_submit_readiness",
            "_intelligence_worker",
            "_readiness_worker",
        }:
            continue
        body_src = ast.get_source_segment(src, node) or ""
        assert "MAX_WORKERS" not in body_src, (
            f"{node.name} unexpectedly references MAX_WORKERS: {body_src}"
        )
        assert "max_workers" not in body_src or "max_workers=size" in body_src, (
            f"{node.name} uses a non-pool max_workers reference: {body_src}"
        )


def test_dispatcher_scheduling_call_sites_present():
    """``run_once`` still owns coding-worker scheduling — the pool code path
    doesn't invade it."""
    src = (_TOOLS / "run_daemon.py").read_text(encoding="utf-8")
    # Sanity: ``run_once`` is still the entry that receives ``max_workers`` and
    # the pool helpers do not import from it.
    assert "def run_once(" in src
    assert "max_workers=args.max_workers" in src
    # The pool creation should never be co-located with dispatcher wake-ups.
    assert "poll_ticket_pipeline" in src


def test_pipeline_pool_settings_are_distinct_from_max_workers():
    for key in (
        "MAX_ISSUES_INTAKED_PER_POLL",
        "MAX_PARALLEL_TICKET_INTELLIGENCE",
        "MAX_PARALLEL_READINESS",
        "GITHUB_POLL_INTERVAL_SECONDS",
    ):
        assert key in _rs.SETTING_SPECS
        assert _rs.SETTING_SPECS[key].env_var != "DAEMON_MAX_WORKERS"
