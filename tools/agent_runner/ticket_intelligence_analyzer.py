"""Hybrid Ticket Intelligence Analyzer.

Orchestrates:
  1. Deterministic feature extraction (ticket_intelligence_extractor)
  2. AI classification via exec_cmd subprocess (provider-agnostic)
  3. JSON validation / normalization
  4. Persistence to ticket_intelligence DB table

Designed to run in a background thread (non-blocking POST endpoint).
AI subprocess timeout: 120 seconds. Failures are persisted, never swallowed.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import shlex
import subprocess
import sys
import time
import traceback
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402
import runtime_settings as _runtime_settings  # noqa: E402
from model_catalog import estimate_cost  # noqa: E402
from ticket_intelligence_extractor import extract as extract_signals  # noqa: E402
from ticket_intelligence_stages import (  # noqa: E402
    STAGE_BUILDING_PROMPT,
    STAGE_COMPLETED,
    STAGE_FAILED,
    STAGE_PARSING_RESULT,
    STAGE_PERSISTING,
    STAGE_STARTING,
    STAGE_WAITING_AI,
)


def _resolve_analysis_timeout(db_path) -> int:
    """Resolve the AI subprocess upper bound through the settings registry.

    Re-read on each call so a DB override of INTELLIGENCE_TIMEOUT_SECONDS is
    picked up by the next ticket without restarting the analyzer process.
    """
    try:
        value = _runtime_settings.get_setting(db_path, "INTELLIGENCE_TIMEOUT_SECONDS")
    except Exception:
        value = None
    try:
        return int(value) if value is not None else 120
    except (TypeError, ValueError):
        return 120

_intel_log = logging.getLogger("intel")


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truncate(value: str | None, limit: int = 500) -> str:
    if not value:
        return ""
    return value if len(value) <= limit else value[:limit] + "…"

_DIFFICULTY_BANDS = [
    (1, 2, "trivial"),
    (3, 4, "simple"),
    (5, 6, "medium"),
    (7, 8, "complex"),
    (9, 10, "critical"),
]

_VALID_AUTONOMOUS_RECS = frozenset({
    "safe",
    "plan_review_required",
    "human_review_required",
    "not_recommended",
})


def _difficulty_label(score: int) -> str:
    for lo, hi, label in _DIFFICULTY_BANDS:
        if lo <= score <= hi:
            return label
    return "medium"


def _clamp_score(val) -> int | None:
    if val is None:
        return None
    try:
        return max(1, min(10, int(val)))
    except (TypeError, ValueError):
        return None


def _extract_json(text: str) -> dict:
    """Extract a JSON object from text that may contain markdown fences."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    raise ValueError(f"no valid JSON found in output (first 300 chars): {text[:300]!r}")


def _normalize(raw: dict, computed_signals: dict) -> dict:
    """Validate and clamp fields from the AI JSON response."""
    difficulty_score = _clamp_score(raw.get("difficulty_score")) or 5
    risk_score = _clamp_score(raw.get("risk_score")) or 5
    difficulty_label = raw.get("difficulty_label") or _difficulty_label(difficulty_score)
    risk_label = raw.get("risk_label", "moderate")

    recommended_model = raw.get("recommended_model", "balanced-code-model")

    input_tokens = raw.get("estimated_input_tokens")
    output_tokens = raw.get("estimated_output_tokens")
    try:
        input_tokens = int(input_tokens) if input_tokens is not None else computed_signals.get("estimated_token_size", 4000)
    except (TypeError, ValueError):
        input_tokens = computed_signals.get("estimated_token_size", 4000)
    try:
        output_tokens = int(output_tokens) if output_tokens is not None else 3000
    except (TypeError, ValueError):
        output_tokens = 3000

    cost_min = raw.get("estimated_cost_min")
    cost_max = raw.get("estimated_cost_max")
    cost_status = raw.get("cost_estimate_status")
    cost_currency = raw.get("cost_currency", "USD")

    if cost_min is None or cost_max is None:
        cost_min, cost_max, cost_status = estimate_cost(recommended_model, input_tokens, output_tokens)

    complexity_factors = raw.get("complexity_factors", [])
    if not isinstance(complexity_factors, list):
        complexity_factors = []

    dependency_hints = raw.get("dependency_hints", [])
    if not isinstance(dependency_hints, list):
        dependency_hints = []

    autonomous_rec = raw.get("autonomous_execution_recommendation", "plan_review_required")
    if autonomous_rec not in _VALID_AUTONOMOUS_RECS:
        autonomous_rec = "plan_review_required"

    queue_rank = raw.get("queue_rank")
    try:
        queue_rank = int(queue_rank) if queue_rank is not None else None
    except (TypeError, ValueError):
        queue_rank = None

    return {
        "difficulty_score": difficulty_score,
        "difficulty_label": difficulty_label,
        "risk_score": risk_score,
        "risk_label": risk_label,
        "complexity_factors": json.dumps(complexity_factors),
        "recommended_model": recommended_model,
        "recommended_model_reason": raw.get("recommended_model_reason") or "",
        "estimated_input_tokens": input_tokens,
        "estimated_output_tokens": output_tokens,
        "estimated_cost_min": cost_min,
        "estimated_cost_max": cost_max,
        "cost_currency": cost_currency,
        "cost_estimate_status": cost_status or "unknown",
        "queue_rank": queue_rank,
        "queue_reason": raw.get("queue_reason") or "",
        "dependency_hints": json.dumps(dependency_hints),
        "parallel_safe_candidate": 1 if raw.get("parallel_safe_candidate") else 0,
        "requires_human_plan_review": 1 if raw.get("requires_human_plan_review") else 0,
        "human_plan_review_reason": raw.get("human_plan_review_reason"),
        "requires_human_code_review": 1 if raw.get("requires_human_code_review") else 0,
        "human_code_review_reason": raw.get("human_code_review_reason"),
        "autonomous_execution_recommendation": autonomous_rec,
        "analysis_summary": raw.get("analysis_summary") or "",
    }


_TEMPLATE_VARS_RE = re.compile(r"\{\{(ticket_content|computed_signals)\}\}")


def _fill_template(template: str, ticket_content: str, computed_signals_json: str) -> str:
    """Single-pass substitution to prevent cross-placeholder injection."""
    values = {"ticket_content": ticket_content, "computed_signals": computed_signals_json}
    return _TEMPLATE_VARS_RE.sub(lambda m: values.get(m.group(1), m.group(0)), template)


def _load_prompt_template(project_root: Path) -> str:
    prompt_path = project_root / "prompts" / "ticket-intelligence-analyzer-prompt.md"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return _INLINE_PROMPT


_INLINE_PROMPT = """\
You are a Ticket Intelligence Analyzer for an AI-assisted software development system.

Analyze the ticket content and computed signals below, then return ONLY a valid JSON object.
Do not include any explanation, markdown, or text outside the JSON object.

For ``dependency_hints``: list only ticket IDs this ticket truly cannot start without
(explicit ``## Depends on`` section or clear prose dependency). Use ``[]`` when none.
Never include illustrative/example ticket IDs from code blocks, sample graphs, or
mock UI data.

## Ticket Content

{{ticket_content}}

## Computed Signals (Python-extracted)

{{computed_signals}}

## Required JSON output

Return exactly this structure (no extra fields, no missing fields):

```json
{
  "difficulty_score": <integer 1-10>,
  "difficulty_label": <"trivial"|"simple"|"medium"|"complex"|"critical">,
  "risk_score": <integer 1-10>,
  "risk_label": <"low"|"moderate"|"high"|"critical">,
  "complexity_factors": ["backend", "database", "UI"],
  "recommended_model": <"local-qwen"|"cheap-fast-model"|"balanced-code-model"|"advanced-reasoning-model">,
  "recommended_model_reason": "<why this model>",
  "estimated_input_tokens": <integer>,
  "estimated_output_tokens": <integer>,
  "estimated_cost_min": <float or null>,
  "estimated_cost_max": <float or null>,
  "cost_currency": "USD",
  "cost_estimate_status": <"estimated"|"unknown">,
  "queue_rank": <integer 1-100>,
  "queue_reason": "<why this rank>",
  "dependency_hints": ["T001", "T042"],
  "parallel_safe_candidate": <true|false>,
  "requires_human_plan_review": <true|false>,
  "human_plan_review_reason": "<reason or null>",
  "requires_human_code_review": <true|false>,
  "human_code_review_reason": "<reason or null>",
  "autonomous_execution_recommendation": <"safe"|"plan_review_required"|"human_review_required"|"not_recommended">,
  "analysis_summary": "<one paragraph summary>"
}
```
"""


def _run_ai_subprocess(
    command: list[str],
    prompt: str,
    env: dict,
    timeout: int,
    *,
    cwd: Path | str | None = None,
) -> tuple[int, str, str, bool, int]:
    """Run the AI subprocess with an enforced upper bound on wall-clock time.

    Uses Popen + communicate(timeout=…) and, on TimeoutExpired, kills the child
    then drains its pipes. Returns ``(rc, stdout, stderr, timed_out, duration_ms)``.
    A zombie child would otherwise pin the background thread to ``running``
    forever — the reason the analyzer was getting stuck.
    """
    proc = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=str(cwd) if cwd is not None else None,
    )
    t0 = time.monotonic()
    timed_out = False
    try:
        stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        try:
            stdout, stderr = proc.communicate()
        except Exception:
            stdout, stderr = "", ""
    rc = proc.returncode if proc.returncode is not None else -1
    duration_ms = int((time.monotonic() - t0) * 1000)
    return rc, stdout or "", stderr or "", timed_out, duration_ms


def _truncate_traceback(limit: int = 2048) -> str:
    """Return the current exception's traceback, truncated to ``limit`` chars."""
    tb = traceback.format_exc()
    if len(tb) <= limit:
        return tb
    return tb[-limit:]


def _set_stage(
    db_path,
    ticket_id: str,
    stage: str,
    *,
    project_id: str | None,
    previous_stage: str | None,
    extra_fields: dict | None = None,
) -> None:
    """Persist a stage transition + append a runtime event + log it.

    Uses this module's ``runtime_db`` binding so tests that monkey-patch
    ``_analyzer.runtime_db`` to a SQLite-only module continue to work.
    """
    fields: dict = {"stage": stage}
    if extra_fields:
        fields.update(extra_fields)
    runtime_db.upsert_ticket_intelligence(db_path, ticket_id, **fields)

    try:
        runtime_db.append_runtime_event(
            db_path,
            ticket_id,
            "ticket_intelligence_stage_changed",
            f"ticket_intelligence stage {previous_stage or '-'} -> {stage}",
            metadata={
                "project_id": project_id,
                "from": previous_stage,
                "to": stage,
            },
        )
    except Exception:
        _intel_log.exception(
            "intel.stage_event_failed project_id=%s ticket_id=%s stage=%s",
            project_id, ticket_id, stage,
        )

    _intel_log.info(
        "intel.stage project_id=%s ticket_id=%s stage=%s previous=%s",
        project_id, ticket_id, stage, previous_stage,
    )


def _emit_failure_event(
    db_path,
    ticket_id: str,
    *,
    project_id: str | None,
    stage: str,
    failure_origin: str,
    analysis_summary: str,
    include_traceback: bool,
) -> None:
    """Best-effort runtime-event emission for a failure branch."""
    metadata: dict = {
        "project_id": project_id,
        "stage": stage,
        "failure_origin": failure_origin,
        "analysis_summary": _truncate(analysis_summary, 500),
    }
    if include_traceback:
        metadata["traceback"] = _truncate_traceback()
    try:
        runtime_db.append_runtime_event(
            db_path,
            ticket_id,
            "ticket_intelligence_analysis_failed",
            f"ticket_intelligence failed at stage={stage} origin={failure_origin}",
            metadata=metadata,
        )
    except Exception:
        _intel_log.exception(
            "intel.failure_event_failed project_id=%s ticket_id=%s stage=%s",
            project_id, ticket_id, stage,
        )


def run_analysis(
    db_path,
    ticket_id: str,
    ticket_content: str,
    exec_cmd: str,
    project_root: Path,
    project_id: str | None = None,
) -> None:
    """Run hybrid ticket intelligence analysis and persist the result.

    Designed to run in a background thread. Drives analysis_status through:
    ``running`` → ``completed`` | ``failed``. Never leaves a row in
    ``queued``/``running``: every failure path persists ``failed_at`` +
    ``failure_origin``, and a top-level ``finally`` re-checks the row to force
    a terminal status if any code escaped without writing one.

    Every persisted row carries a ``stage`` value naming the exact pipeline
    position (T210) so a stuck analysis can be diagnosed from the DB alone.
    """
    _intel_log.info(
        "intel.started project_id=%s ticket_id=%s db_path=%s stage=%s",
        project_id, ticket_id, db_path, STAGE_STARTING,
    )

    # ``current_stage`` mirrors what's currently persisted, so every failure
    # branch can carry the precise stage at which the failure occurred.
    current_stage = STAGE_STARTING
    computed_signals_json: str | None = None

    try:
        try:
            _set_stage(
                db_path, ticket_id, STAGE_STARTING,
                project_id=project_id,
                previous_stage=None,
                extra_fields={
                    "analysis_status": "running",
                    "started_at": _now_iso(),
                },
            )
            runtime_db.append_runtime_event(
                db_path,
                ticket_id,
                "ticket_intelligence_analysis_started",
                f"ticket_intelligence analysis started ticket_id={ticket_id}",
                metadata={"project_id": project_id, "stage": STAGE_STARTING},
            )

            computed_signals = extract_signals(ticket_content)
            computed_signals_json = json.dumps(computed_signals)
            _intel_log.info(
                "intel.step.signals_extracted ticket_id=%s stage=%s signals_count=%d",
                ticket_id, current_stage,
                len(computed_signals) if isinstance(computed_signals, dict) else 0,
            )

            _set_stage(
                db_path, ticket_id, STAGE_BUILDING_PROMPT,
                project_id=project_id,
                previous_stage=current_stage,
            )
            current_stage = STAGE_BUILDING_PROMPT

            template = _load_prompt_template(project_root)
            prompt = _fill_template(template, ticket_content, computed_signals_json)
            _intel_log.info(
                "intel.step.prompt_built ticket_id=%s stage=%s prompt_len=%d",
                ticket_id, current_stage, len(prompt),
            )

            command = shlex.split(exec_cmd)
            if not command:
                raise ValueError("exec_cmd is empty")
            # Non-interactive mode — matches run_analysis / run_scripts.
            if "--print" not in command and "-p" not in command:
                command = command + ["--print"]

            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            _set_stage(
                db_path, ticket_id, STAGE_WAITING_AI,
                project_id=project_id,
                previous_stage=current_stage,
            )
            current_stage = STAGE_WAITING_AI

            # Re-read every run so a DB override of INTELLIGENCE_TIMEOUT_SECONDS
            # is picked up without restarting the analyzer process.
            analysis_timeout = _resolve_analysis_timeout(db_path)
            _intel_log.info(
                "intel.ai_request.started project_id=%s ticket_id=%s stage=%s exec_cmd=%s "
                "timeout=%ds prompt_size=%d",
                project_id, ticket_id, current_stage, _truncate(exec_cmd, 200),
                analysis_timeout, len(prompt),
            )
            runtime_db.append_runtime_event(
                db_path,
                ticket_id,
                "ticket_intelligence_ai_process_started",
                f"ticket_intelligence AI subprocess started ticket_id={ticket_id}",
                metadata={
                    "project_id": project_id,
                    "stage": current_stage,
                    "timeout": analysis_timeout,
                    "prompt_size": len(prompt),
                },
            )

            rc, stdout, stderr, timed_out, duration_ms = _run_ai_subprocess(
                command, prompt, env, analysis_timeout, cwd=project_root,
            )

            _intel_log.info(
                "intel.ai_request.completed project_id=%s ticket_id=%s stage=%s rc=%s "
                "stdout_len=%d stderr_len=%d duration_ms=%d timed_out=%s",
                project_id, ticket_id, current_stage, rc, len(stdout), len(stderr),
                duration_ms, timed_out,
            )
            runtime_db.append_runtime_event(
                db_path,
                ticket_id,
                "ticket_intelligence_ai_process_completed",
                f"ticket_intelligence AI subprocess completed ticket_id={ticket_id} rc={rc}",
                metadata={
                    "project_id": project_id,
                    "stage": current_stage,
                    "rc": rc,
                    "duration_ms": duration_ms,
                    "timed_out": timed_out,
                },
            )

            if timed_out:
                summary = f"Analysis timed out after {analysis_timeout} seconds."
                _set_stage(
                    db_path, ticket_id, STAGE_FAILED,
                    project_id=project_id,
                    previous_stage=current_stage,
                    extra_fields={
                        "analysis_status": "failed",
                        "analysis_summary": summary,
                        "computed_signals_json": computed_signals_json,
                        "failed_at": _now_iso(),
                        "failure_origin": "timeout",
                    },
                )
                _intel_log.error(
                    "intel.failed project_id=%s ticket_id=%s stage=%s db_path=%s "
                    "reason=timeout duration_ms=%d",
                    project_id, ticket_id, current_stage, db_path, duration_ms,
                )
                _emit_failure_event(
                    db_path, ticket_id,
                    project_id=project_id,
                    stage=current_stage,
                    failure_origin="timeout",
                    analysis_summary=summary,
                    include_traceback=False,
                )
                return

            if rc != 0 or not stdout.strip():
                summary = f"AI call failed (rc={rc})"
                detail = (stderr or stdout or "").strip()
                if detail:
                    summary += f": {detail[:500]}"
                _set_stage(
                    db_path, ticket_id, STAGE_FAILED,
                    project_id=project_id,
                    previous_stage=current_stage,
                    extra_fields={
                        "analysis_status": "failed",
                        "analysis_summary": summary,
                        "computed_signals_json": computed_signals_json,
                        "failed_at": _now_iso(),
                        "failure_origin": "nonzero_rc",
                    },
                )
                _intel_log.error(
                    "intel.failed project_id=%s ticket_id=%s stage=%s db_path=%s "
                    "reason=nonzero_rc rc=%s stderr=%s",
                    project_id, ticket_id, current_stage, db_path, rc, _truncate(stderr, 200),
                )
                _emit_failure_event(
                    db_path, ticket_id,
                    project_id=project_id,
                    stage=current_stage,
                    failure_origin="nonzero_rc",
                    analysis_summary=summary,
                    include_traceback=False,
                )
                return

            _set_stage(
                db_path, ticket_id, STAGE_PARSING_RESULT,
                project_id=project_id,
                previous_stage=current_stage,
            )
            current_stage = STAGE_PARSING_RESULT

            try:
                raw = _extract_json(stdout)
            except ValueError as exc:
                summary = f"JSON parse error: {exc}"
                _set_stage(
                    db_path, ticket_id, STAGE_FAILED,
                    project_id=project_id,
                    previous_stage=current_stage,
                    extra_fields={
                        "analysis_status": "failed",
                        "analysis_summary": summary,
                        "computed_signals_json": computed_signals_json,
                        "failed_at": _now_iso(),
                        "failure_origin": "json_parse",
                    },
                )
                _intel_log.exception(
                    "intel.failed project_id=%s ticket_id=%s stage=%s db_path=%s "
                    "reason=json_parse",
                    project_id, ticket_id, current_stage, db_path,
                )
                _emit_failure_event(
                    db_path, ticket_id,
                    project_id=project_id,
                    stage=current_stage,
                    failure_origin="json_parse",
                    analysis_summary=summary,
                    include_traceback=True,
                )
                return

            _intel_log.info(
                "intel.step.json_parsed ticket_id=%s stage=%s fields=%d",
                ticket_id, current_stage,
                len(raw) if isinstance(raw, dict) else 0,
            )

            normalized = _normalize(raw, computed_signals)

            _set_stage(
                db_path, ticket_id, STAGE_PERSISTING,
                project_id=project_id,
                previous_stage=current_stage,
            )
            current_stage = STAGE_PERSISTING

            _set_stage(
                db_path, ticket_id, STAGE_COMPLETED,
                project_id=project_id,
                previous_stage=current_stage,
                extra_fields={
                    "analysis_status": "completed",
                    "computed_signals_json": computed_signals_json,
                    "completed_at": _now_iso(),
                    **normalized,
                },
            )
            current_stage = STAGE_COMPLETED
            _intel_log.info(
                "intel.persisted project_id=%s ticket_id=%s stage=%s status=completed db_path=%s",
                project_id, ticket_id, current_stage, db_path,
            )
            runtime_db.append_runtime_event(
                db_path,
                ticket_id,
                "ticket_intelligence_analysis_completed",
                f"ticket_intelligence analysis completed ticket_id={ticket_id}",
                metadata={"project_id": project_id, "stage": current_stage},
            )
            try:
                from ticket_pipeline import maybe_run_readiness_after_intelligence  # noqa: WPS433

                maybe_run_readiness_after_intelligence(
                    db_path, ticket_id, ticket_content, project_root,
                    project_id=project_id,
                )
            except Exception:
                _intel_log.exception(
                    "intel.readiness_chain_failed project_id=%s ticket_id=%s",
                    project_id, ticket_id,
                )

        except Exception as exc:
            summary = f"Unexpected error: {exc}"
            try:
                _set_stage(
                    db_path, ticket_id, STAGE_FAILED,
                    project_id=project_id,
                    previous_stage=current_stage,
                    extra_fields={
                        "analysis_status": "failed",
                        "analysis_summary": summary,
                        "failed_at": _now_iso(),
                        "failure_origin": "exception",
                    },
                )
            except Exception:
                _intel_log.exception(
                    "intel.persist_failure_failed project_id=%s ticket_id=%s stage=%s",
                    project_id, ticket_id, current_stage,
                )
            _intel_log.exception(
                "intel.failed project_id=%s ticket_id=%s stage=%s db_path=%s "
                "reason=exception detail=%s",
                project_id, ticket_id, current_stage, db_path, _truncate(str(exc), 200),
            )
            _emit_failure_event(
                db_path, ticket_id,
                project_id=project_id,
                stage=current_stage,
                failure_origin="exception",
                analysis_summary=summary,
                include_traceback=True,
            )
    finally:
        # Last-chance guard: if any code path escaped above (BaseException, or
        # the except branch's persistence itself raised) without writing a
        # terminal status, force the row to ``failed`` so no analysis stays in
        # ``queued`` / ``running``.
        try:
            row = runtime_db.get_ticket_intelligence(db_path, ticket_id)
            if row and row.get("analysis_status") in ("queued", "running"):
                try:
                    _set_stage(
                        db_path, ticket_id, STAGE_FAILED,
                        project_id=project_id,
                        previous_stage=current_stage,
                        extra_fields={
                            "analysis_status": "failed",
                            "analysis_summary": "Analyzer exited without terminal status",
                            "failed_at": _now_iso(),
                            "failure_origin": "finally_guard",
                        },
                    )
                except Exception:
                    _intel_log.exception(
                        "intel.finally_guard_persist_failed project_id=%s ticket_id=%s stage=%s",
                        project_id, ticket_id, current_stage,
                    )
                _intel_log.error(
                    "intel.persisted project_id=%s ticket_id=%s stage=%s status=failed "
                    "db_path=%s reason=finally_guard",
                    project_id, ticket_id, STAGE_FAILED, db_path,
                )
                _emit_failure_event(
                    db_path, ticket_id,
                    project_id=project_id,
                    stage=current_stage,
                    failure_origin="finally_guard",
                    analysis_summary="Analyzer exited without terminal status",
                    include_traceback=False,
                )
        except Exception:
            _intel_log.exception(
                "intel.finally_guard failed project_id=%s ticket_id=%s stage=%s",
                project_id, ticket_id, current_stage,
            )
