"""Tests for ``scripts_validator.validate_generated_files``.

These pin the real failure modes observed in PR #114:
  - bootstrap.sh wrapped in ```bash ... ``` markdown fences;
  - start.sh / stop.sh / healthcheck.sh reduced to a one-sentence English
    description ("Starts supervisor → Docker stack → daemon …");
  - deployment.md replaced by a one-liner summary.

The validator returns a list of error strings; an empty list means
"ok to write to disk". Empty input is treated as a missing-files error
to keep ``run_scripts.main`` from spinning up an empty PR.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

from scripts_validator import (  # noqa: E402
    REQUIRED_FILES,
    validate_generated_files,
)


# ── helpers ───────────────────────────────────────────────────────────────────

_GOOD_BODY = """\
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/../.."
docker compose up -d
echo "started"
"""

_GOOD_DEPLOYMENT_MD = """\
# Deployment Guide

## Overview

A real deployment guide with multiple sections. The validator's
threshold (~300 bytes, two headings) makes a one-liner summary fail.

## Scripts

| Script | Purpose |
|--------|---------|
| bootstrap.sh | First-time setup |
| build.sh | Build images |

## Environment variables

| Variable | Default |
|----------|---------|
| AI_DEV_FACTORY_RUNTIME_ROOT | ~/runtime/ai-dev-factory |
"""


def _make_valid_set() -> dict[str, str]:
    """Build a complete, passing set of generated files."""
    files = {p: _GOOD_BODY for p in REQUIRED_FILES if p.endswith(".sh")}
    files[".ai-dev-factory/deployment.md"] = _GOOD_DEPLOYMENT_MD
    return files


# ── 1. Happy path ────────────────────────────────────────────────────────────

def test_valid_set_returns_no_errors():
    assert validate_generated_files(_make_valid_set()) == []


# ── 2. Markdown-fence detection (real PR #114 bug) ───────────────────────────

def test_markdown_fence_in_shell_script_is_rejected():
    files = _make_valid_set()
    files[".ai-dev-factory/scripts/bootstrap.sh"] = (
        "```bash\n#!/usr/bin/env bash\nset -euo pipefail\necho hi\n```\n"
    )
    errors = validate_generated_files(files)
    assert any(
        "bootstrap.sh" in e and "markdown code fence" in e for e in errors
    ), f"expected fence error, got: {errors}"


def test_inline_triple_backtick_anywhere_in_script_is_rejected():
    files = _make_valid_set()
    files[".ai-dev-factory/scripts/build.sh"] = _GOOD_BODY + "\n# ```\n"
    errors = validate_generated_files(files)
    assert any("```" in e or "markdown code fence" in e for e in errors)


def test_single_backticks_in_command_substitution_are_allowed():
    """``$(...)`` and bare backticks for command substitution are fine."""
    files = _make_valid_set()
    files[".ai-dev-factory/scripts/healthcheck.sh"] = (
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        'curl -sf http://localhost:8080/health && echo "ok"\n'
        "REV=$(git rev-parse HEAD)\n"
        'echo "deployed: $REV"\n'
    )
    assert validate_generated_files(files) == []


# ── 3. Missing shebang ────────────────────────────────────────────────────────

def test_missing_shebang_is_rejected():
    files = _make_valid_set()
    files[".ai-dev-factory/scripts/start.sh"] = (
        "set -euo pipefail\ndocker compose up -d\necho started\n"
    )
    errors = validate_generated_files(files)
    assert any("start.sh" in e and "shebang" in e for e in errors)


def test_blank_lines_before_shebang_are_tolerated():
    files = _make_valid_set()
    files[".ai-dev-factory/scripts/start.sh"] = "\n\n" + _GOOD_BODY
    assert validate_generated_files(files) == []


# ── 4. Prose-as-script (the most pernicious PR #114 bug) ─────────────────────

def test_one_line_english_description_is_rejected():
    files = _make_valid_set()
    files[".ai-dev-factory/scripts/start.sh"] = (
        "Starts supervisor → Docker stack → daemon (if `GITHUB_REPO` is set), "
        "with PID tracking in `.ai-dev-factory/run/`.\n"
    )
    errors = validate_generated_files(files)
    msg = "\n".join(errors)
    assert "start.sh" in msg
    # Either the shebang OR the size OR the not-shell-tokens rule triggers.
    assert any(s in msg for s in ("shebang", "body too small", "does not look"))


def test_prose_body_after_shebang_is_rejected():
    """LLM might emit ``#!/usr/bin/env bash`` and then prose, which is
    even nastier because shebang is correct but body is garbage."""
    files = _make_valid_set()
    files[".ai-dev-factory/scripts/healthcheck.sh"] = (
        "#!/usr/bin/env bash\n"
        "Probes api, web, supervisor, daemon and the deploy-profile primary "
        "healthcheck with retries=3 / delay=5s / timeout=30s.\n"
    )
    errors = validate_generated_files(files)
    assert any(
        "healthcheck.sh" in e and ("does not look" in e or "body too small" in e)
        for e in errors
    )


# ── 5. deployment.md size + structure ────────────────────────────────────────

def test_one_line_summary_deployment_md_is_rejected():
    files = _make_valid_set()
    files[".ai-dev-factory/deployment.md"] = (
        "Updated — covers project overview, all six scripts, environment "
        "variable table, runtime dependencies, and known operational "
        "constraints.\n"
    )
    errors = validate_generated_files(files)
    msg = "\n".join(errors)
    assert "deployment.md" in msg
    assert "too small" in msg or "heading" in msg


def test_deployment_md_with_only_title_is_rejected():
    files = _make_valid_set()
    files[".ai-dev-factory/deployment.md"] = "# Deployment\n" + ("x " * 200) + "\n"
    errors = validate_generated_files(files)
    assert any("heading" in e for e in errors)


# ── 6. Missing required files ────────────────────────────────────────────────

def test_missing_required_files_listed_individually():
    files = {".ai-dev-factory/scripts/bootstrap.sh": _GOOD_BODY}
    errors = validate_generated_files(files)
    missing = [e for e in errors if "missing required FILE block" in e]
    assert len(missing) == len(REQUIRED_FILES) - 1


def test_empty_input_reports_all_missing_files():
    errors = validate_generated_files({})
    missing = [e for e in errors if "missing required FILE block" in e]
    assert len(missing) == len(REQUIRED_FILES)


# ── 7. Multiple issues reported together ─────────────────────────────────────

def test_multiple_errors_are_all_reported():
    """The validator must not short-circuit — operators see every issue
    at once and can fix the prompt iteratively."""
    files = _make_valid_set()
    files[".ai-dev-factory/scripts/start.sh"] = (
        "```bash\nStarts the stack.\n```\n"
    )
    files[".ai-dev-factory/deployment.md"] = "Just a sentence.\n"
    errors = validate_generated_files(files)
    assert any("start.sh" in e and "markdown code fence" in e for e in errors)
    assert any("deployment.md" in e for e in errors)
