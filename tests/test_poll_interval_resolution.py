"""T221 fix — GITHUB_POLL_INTERVAL_SECONDS is consumed at the sleep site.

The prior implementation registered the setting but never read it: the daemon
always slept ``args.interval`` seconds (default 30, hard-coded in the launcher
command), so the demo-friendly 5 s cadence advertised in the docs was
unreachable without a bespoke CLI override.

These tests lock in the fix: ``_resolve_poll_interval`` returns the setting
value when ``--interval`` is omitted, and honours the CLI override when set.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import _resolve_poll_interval  # noqa: E402


def _make_args(interval):
    return argparse.Namespace(interval=interval)


def test_cli_interval_overrides_setting(monkeypatch):
    monkeypatch.setenv("GITHUB_POLL_INTERVAL_SECONDS", "5")
    assert _resolve_poll_interval(_make_args(17)) == 17


def test_env_setting_used_when_cli_omitted(monkeypatch):
    monkeypatch.setenv("GITHUB_POLL_INTERVAL_SECONDS", "5")
    # _ensure_db can be flaky in a test env; the setting resolves from env
    # regardless of whether the DB is reachable.
    with patch("run_daemon._ensure_db", return_value=None):
        assert _resolve_poll_interval(_make_args(None)) == 5


def test_spec_default_used_when_nothing_set(monkeypatch):
    monkeypatch.delenv("GITHUB_POLL_INTERVAL_SECONDS", raising=False)
    with patch("run_daemon._ensure_db", return_value=None):
        # Spec default from runtime_settings is 5.
        assert _resolve_poll_interval(_make_args(None)) == 5


def test_invalid_env_falls_back_to_safe_default(monkeypatch):
    monkeypatch.setenv("GITHUB_POLL_INTERVAL_SECONDS", "abc")
    with patch("run_daemon._ensure_db", return_value=None):
        # get_setting_int_positive uses safe_default=30 at this call site.
        assert _resolve_poll_interval(_make_args(None)) == 30


def test_zero_env_falls_back_to_safe_default(monkeypatch):
    monkeypatch.setenv("GITHUB_POLL_INTERVAL_SECONDS", "0")
    with patch("run_daemon._ensure_db", return_value=None):
        assert _resolve_poll_interval(_make_args(None)) == 30
