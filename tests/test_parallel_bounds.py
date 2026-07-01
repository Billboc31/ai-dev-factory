"""T221 — enforce ``MAX_PARALLEL_TICKET_INTELLIGENCE`` / ``MAX_PARALLEL_READINESS``.

Directly exercise the ``concurrent.futures`` pool created in ``run_daemon`` by
submitting more work than the pool can execute at once and observing the peak
concurrency via a barrier. If the pool were unbounded we would see the peak
climb to the number of submitted tasks.
"""

from __future__ import annotations

import concurrent.futures
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

import run_daemon  # noqa: E402


def _run_bounded(pool_attr: str, size_setting: str, monkeypatch) -> int:
    """Submit ``2 * size + 2`` blocking tasks and return the observed peak."""
    monkeypatch.setattr(run_daemon, pool_attr, None, raising=False)
    monkeypatch.setattr(
        run_daemon._runtime_settings,
        "get_setting_int_positive",
        lambda db, key, default: 4 if key == size_setting else default,
    )

    total_tasks = 10  # > pool size (4) so we would exceed the cap if unbounded
    peak = 0
    running = 0
    lock = threading.Lock()
    release = threading.Event()

    def _stage_fn():
        nonlocal peak, running
        with lock:
            running += 1
            if running > peak:
                peak = running
        # Hold the thread until the test releases it. Even a small hold is
        # enough to exceed the pool cap when the pool is unbounded.
        release.wait(timeout=5)
        with lock:
            running -= 1

    # Force pool creation. ``_init_pipeline_pools`` reads settings via the
    # patched ``get_setting_int_positive`` above, so the pool sizes are 4.
    run_daemon._init_pipeline_pools(db_path=None)
    pool: concurrent.futures.ThreadPoolExecutor = getattr(run_daemon, pool_attr)
    assert pool is not None

    futures = [pool.submit(_stage_fn) for _ in range(total_tasks)]
    time.sleep(0.2)  # give the executor time to fill up
    release.set()
    for fut in futures:
        fut.result(timeout=10)

    return peak


def test_intelligence_pool_bounded(monkeypatch):
    run_daemon._shutdown_pipeline_pools()
    try:
        peak = _run_bounded(
            pool_attr="_intel_pool",
            size_setting="MAX_PARALLEL_TICKET_INTELLIGENCE",
            monkeypatch=monkeypatch,
        )
        assert peak == 4
    finally:
        run_daemon._shutdown_pipeline_pools()


def test_readiness_pool_bounded(monkeypatch):
    run_daemon._shutdown_pipeline_pools()
    try:
        peak = _run_bounded(
            pool_attr="_readiness_pool",
            size_setting="MAX_PARALLEL_READINESS",
            monkeypatch=monkeypatch,
        )
        assert peak == 4
    finally:
        run_daemon._shutdown_pipeline_pools()
