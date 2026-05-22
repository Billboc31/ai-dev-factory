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


# ── 8. Safety lint — broad process killing ────────────────────────────────────

def _wrap(body: str) -> dict[str, str]:
    """Embed ``body`` inside a complete passing fixture, replacing only
    the stop.sh content. Lets us assert the safety-lint trigger without
    tripping any of the structural rules."""
    files = _make_valid_set()
    files[".ai-dev-factory/scripts/stop.sh"] = body
    return files


_STOP_PREFIX = (
    "#!/usr/bin/env bash\n"
    "set -euo pipefail\n"
    'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n'
    'cd "$SCRIPT_DIR/../.."\n'
)


def test_pkill_dash_f_run_daemon_is_rejected():
    """The exact PR #114 stop.sh failure: kills every developer's daemon."""
    body = _STOP_PREFIX + 'pkill -f run_daemon.py || true\n'
    errors = validate_generated_files(_wrap(body))
    matching = [e for e in errors if "stop.sh" in e and "pkill -f" in e]
    assert matching, f"expected pkill -f lint, got: {errors}"
    assert "B2/B3" in matching[0] or "supervisor" in matching[0]


def test_pkill_dash_f_uvicorn_is_rejected():
    body = _STOP_PREFIX + 'pkill -f "uvicorn services.supervisor.main" || true\n'
    errors = validate_generated_files(_wrap(body))
    assert any("pkill -f" in e for e in errors)


def test_pkill_dash_capital_F_pidfile_is_allowed():
    """`pkill -F <pidfile>` reads PIDs from a file — the safe form."""
    body = _STOP_PREFIX + (
        'PIDFILE=".ai-dev-factory/run/daemon.pid"\n'
        '[ -f "$PIDFILE" ] && pkill -F "$PIDFILE" || true\n'
    )
    errors = validate_generated_files(_wrap(body))
    assert not any("pkill" in e for e in errors), f"unexpected pkill error: {errors}"


def test_killall_is_rejected():
    body = _STOP_PREFIX + 'killall daemon || true\n'
    errors = validate_generated_files(_wrap(body))
    assert any("killall" in e for e in errors)


def test_pgrep_dash_f_run_daemon_is_rejected():
    body = _STOP_PREFIX + (
        'if pgrep -f run_daemon.py >/dev/null; then\n'
        '  echo "daemon already running" >&2\n'
        '  exit 1\n'
        'fi\n'
    )
    errors = validate_generated_files(_wrap(body))
    assert any("run_daemon.py" in e and "system-wide" in e for e in errors)


# ── 9. Safety lint — destructive filesystem operations ────────────────────────

def test_rm_rf_root_is_rejected():
    body = _STOP_PREFIX + 'rm -rf /\n'
    errors = validate_generated_files(_wrap(body))
    assert any("catastrophic" in e for e in errors)


def test_rm_rf_root_glob_is_rejected():
    body = _STOP_PREFIX + 'rm -rf /*\n'
    errors = validate_generated_files(_wrap(body))
    assert any("catastrophic" in e for e in errors)


def test_rm_rf_home_is_rejected():
    body = _STOP_PREFIX + 'rm -rf "$HOME"\n'
    errors = validate_generated_files(_wrap(body))
    assert any("$HOME" in e for e in errors)


def test_rm_rf_tilde_is_rejected():
    body = _STOP_PREFIX + 'rm -rf ~\n'
    errors = validate_generated_files(_wrap(body))
    assert any("wipes the user" in e for e in errors)


def test_rm_rf_unguarded_variable_is_rejected():
    body = _STOP_PREFIX + 'rm -rf "$TARGET_DIR"\n'
    errors = validate_generated_files(_wrap(body))
    assert any("unguarded" in e and "TARGET_DIR" in e for e in errors)


def test_rm_rf_guarded_variable_is_allowed():
    """The bash ``${VAR:?msg}`` form aborts when VAR is unset/empty."""
    body = _STOP_PREFIX + 'rm -rf "${TARGET_DIR:?TARGET_DIR must be set}"\n'
    errors = validate_generated_files(_wrap(body))
    assert not any("rm -rf" in e for e in errors), f"unexpected rm -rf error: {errors}"


def test_rm_rf_literal_project_path_is_allowed():
    """Literal project-relative paths are fine — no variable to guard."""
    body = _STOP_PREFIX + 'rm -rf ".ai-dev-factory/run"\n'
    errors = validate_generated_files(_wrap(body))
    assert not any("rm -rf" in e for e in errors), f"unexpected rm -rf error: {errors}"


# ── 10. Safety lint — hard-coded user paths ───────────────────────────────────

def test_macos_user_path_is_rejected():
    body = _STOP_PREFIX + 'cd /Users/pierrebocquet/runtime/ai-dev-factory\n'
    errors = validate_generated_files(_wrap(body))
    assert any("/Users/" in e for e in errors)


def test_linux_user_path_is_rejected():
    body = _STOP_PREFIX + 'cd /home/jenkins/work/ai-dev-factory\n'
    errors = validate_generated_files(_wrap(body))
    assert any("/home/" in e for e in errors)


def test_user_path_env_var_is_allowed():
    body = _STOP_PREFIX + (
        '[ -f deploy/.env ] && source deploy/.env || true\n'
        'cd "$AI_DEV_FACTORY_PROJECT_ROOT"\n'
    )
    errors = validate_generated_files(_wrap(body))
    assert not any("hard-coded" in e for e in errors), errors


# ── 11. Safety lint — Docker blast radius ─────────────────────────────────────

def test_docker_system_prune_is_rejected():
    body = _STOP_PREFIX + 'docker system prune -af\n'
    errors = validate_generated_files(_wrap(body))
    assert any("docker system prune" in e for e in errors)


def test_docker_volume_prune_is_rejected():
    body = _STOP_PREFIX + 'docker volume prune -f\n'
    errors = validate_generated_files(_wrap(body))
    assert any("prune" in e for e in errors)


def test_docker_compose_down_volumes_without_project_name_is_rejected():
    body = _STOP_PREFIX + 'docker compose down -v\n'
    errors = validate_generated_files(_wrap(body))
    assert any("docker compose down -v" in e for e in errors)


def test_docker_compose_down_with_project_name_is_allowed():
    body = _STOP_PREFIX + 'docker compose -p ai-dev-factory down -v\n'
    errors = validate_generated_files(_wrap(body))
    assert not any("docker compose down" in e for e in errors), errors


def test_docker_compose_down_without_volumes_is_allowed():
    """Plain `docker compose down` (no `-v`) is fine — it only removes
    the containers/networks of the current compose project."""
    body = _STOP_PREFIX + 'docker compose down\n'
    errors = validate_generated_files(_wrap(body))
    assert not any("docker compose down" in e for e in errors), errors


# ── 12. Comments documenting anti-patterns must not trigger lint ──────────────

def test_anti_patterns_inside_comments_are_ignored():
    """Real scripts should be able to *document* what NOT to do without
    failing validation. Only actual commands are scanned."""
    body = _STOP_PREFIX + (
        '# Never use: pkill -f run_daemon.py — kills other devs\' daemons.\n'
        '# Never call killall.\n'
        '# Never use: rm -rf /  or rm -rf $HOME.\n'
        '# Never: docker system prune.\n'
        '#\n'
        'PIDFILE=".ai-dev-factory/run/daemon.pid"\n'
        '[ -f "$PIDFILE" ] && pkill -F "$PIDFILE" || true\n'
    )
    errors = validate_generated_files(_wrap(body))
    relevant = [
        e for e in errors
        if any(s in e for s in (
            "pkill -f", "killall", "rm -rf", "docker system prune"
        ))
    ]
    assert not relevant, f"comments should not trigger safety lint: {relevant}"


def test_parameter_expansion_hash_is_not_treated_as_comment():
    """``${VAR#prefix}`` is a bash parameter expansion, not a comment.
    The comment-stripping must preserve it."""
    body = _STOP_PREFIX + (
        'SHORT="${BRANCH#refs/heads/}"\n'
        'echo "$SHORT"\n'
    )
    # No safety rule should trigger — and the script should still
    # look like a shell script (structural check stays green).
    errors = validate_generated_files(_wrap(body))
    assert not any(s in "\n".join(errors) for s in (
        "pkill", "killall", "rm -rf", "does not look",
    )), errors


# ── 13. The full PR #114 stop.sh fails every relevant rule ────────────────────

def test_pr_114_stop_sh_is_rejected():
    """Pin the exact body shape that PR #114 produced — every safety
    rule that applies should fire."""
    body = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        '\n'
        '# Stop daemon\n'
        'pkill -f run_daemon.py || true\n'
        '\n'
        '# Stop docker stack\n'
        'docker compose down -v\n'
        '\n'
        '# Stop supervisor\n'
        'pkill -f "uvicorn services.supervisor.main" || true\n'
    )
    errors = validate_generated_files(_wrap(body))
    assert any("pkill -f" in e for e in errors)
    assert any("docker compose down -v" in e for e in errors)
