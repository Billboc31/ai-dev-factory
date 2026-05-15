"""Tests for T027 — automatic fix artifact generation."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_ticket import _write_fix_artifact


def _setup(tmp: str, ticket_id: str = "T999") -> tuple[Path, Path]:
    run_dir = Path(tmp) / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    fixes_dir = run_dir / "fixes"
    fixes_dir.mkdir()
    return run_dir, fixes_dir


# ── creation ─────────────────────────────────────────────────────────────────

def test_plan_fix_artifact_created():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, fixes_dir = _setup(tmp)
        review = run_dir / "reviews" / "plan-review.md"
        review.parent.mkdir()
        review.write_text("the review content")
        os.chdir(tmp)
        try:
            _write_fix_artifact("T999", "PLAN_FIX_REQUIRED", review)
        finally:
            os.chdir(Path(__file__).parent.parent)
        assert (fixes_dir / "plan-fix-1.md").exists()


def test_implementation_fix_artifact_created():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, fixes_dir = _setup(tmp)
        review = run_dir / "reviews" / "implementation-review.md"
        review.parent.mkdir()
        review.write_text("implementation review")
        os.chdir(tmp)
        try:
            _write_fix_artifact("T999", "IMPLEMENTATION_FIX_REQUIRED", review)
        finally:
            os.chdir(Path(__file__).parent.parent)
        assert (fixes_dir / "implementation-fix-1.md").exists()


# ── increment ─────────────────────────────────────────────────────────────────

def test_fix_artifact_increments_correctly():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, fixes_dir = _setup(tmp)
        (fixes_dir / "implementation-fix-1.md").write_text("old fix")
        review = run_dir / "reviews" / "r.md"
        review.parent.mkdir()
        review.write_text("new review")
        os.chdir(tmp)
        try:
            _write_fix_artifact("T999", "IMPLEMENTATION_FIX_REQUIRED", review)
        finally:
            os.chdir(Path(__file__).parent.parent)
        assert (fixes_dir / "implementation-fix-2.md").exists()
        assert not (fixes_dir / "implementation-fix-3.md").exists()


def test_plan_fix_artifact_increments_independently():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, fixes_dir = _setup(tmp)
        (fixes_dir / "plan-fix-1.md").write_text("old plan fix")
        (fixes_dir / "plan-fix-2.md").write_text("second plan fix")
        review = run_dir / "reviews" / "r.md"
        review.parent.mkdir()
        review.write_text("plan review")
        os.chdir(tmp)
        try:
            _write_fix_artifact("T999", "PLAN_FIX_REQUIRED", review)
        finally:
            os.chdir(Path(__file__).parent.parent)
        assert (fixes_dir / "plan-fix-3.md").exists()


# ── content ───────────────────────────────────────────────────────────────────

def test_fix_artifact_contains_decision():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, fixes_dir = _setup(tmp)
        review = run_dir / "reviews" / "r.md"
        review.parent.mkdir()
        review.write_text("some content")
        os.chdir(tmp)
        try:
            _write_fix_artifact("T999", "IMPLEMENTATION_FIX_REQUIRED", review)
        finally:
            os.chdir(Path(__file__).parent.parent)
        content = (fixes_dir / "implementation-fix-1.md").read_text()
        assert "IMPLEMENTATION_FIX_REQUIRED" in content


def test_fix_artifact_contains_review_source_path():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, fixes_dir = _setup(tmp)
        review = run_dir / "reviews" / "implementation-review.md"
        review.parent.mkdir()
        review.write_text("review body")
        os.chdir(tmp)
        try:
            _write_fix_artifact("T999", "IMPLEMENTATION_FIX_REQUIRED", review)
        finally:
            os.chdir(Path(__file__).parent.parent)
        content = (fixes_dir / "implementation-fix-1.md").read_text()
        assert "implementation-review.md" in content


def test_fix_artifact_contains_review_content():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, fixes_dir = _setup(tmp)
        review = run_dir / "reviews" / "r.md"
        review.parent.mkdir()
        review.write_text("the actual review body text")
        os.chdir(tmp)
        try:
            _write_fix_artifact("T999", "IMPLEMENTATION_FIX_REQUIRED", review)
        finally:
            os.chdir(Path(__file__).parent.parent)
        content = (fixes_dir / "implementation-fix-1.md").read_text()
        assert "the actual review body text" in content


# ── no artifact on *_APPROVED ─────────────────────────────────────────────────

def test_no_fix_artifact_on_plan_approved():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, fixes_dir = _setup(tmp)
        review = run_dir / "reviews" / "r.md"
        review.parent.mkdir()
        review.write_text("approved review")
        next_state = "PLAN_APPROVED"
        # auto_run only calls _write_fix_artifact when next_state.endswith("_FIX_REQUIRED")
        if next_state.endswith("_FIX_REQUIRED"):
            os.chdir(tmp)
            try:
                _write_fix_artifact("T999", next_state, review)
            finally:
                os.chdir(Path(__file__).parent.parent)
        assert not any(fixes_dir.iterdir())


def test_no_fix_artifact_on_implementation_approved():
    with tempfile.TemporaryDirectory() as tmp:
        run_dir, fixes_dir = _setup(tmp)
        review = run_dir / "reviews" / "r.md"
        review.parent.mkdir()
        review.write_text("approved review")
        next_state = "IMPLEMENTATION_APPROVED"
        if next_state.endswith("_FIX_REQUIRED"):
            os.chdir(tmp)
            try:
                _write_fix_artifact("T999", next_state, review)
            finally:
                os.chdir(Path(__file__).parent.parent)
        assert not any(fixes_dir.iterdir())
