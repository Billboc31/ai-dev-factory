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

import json
import logging
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402
from model_catalog import estimate_cost  # noqa: E402
from ticket_intelligence_extractor import extract as extract_signals  # noqa: E402

_ANALYSIS_TIMEOUT = 120

_intel_log = logging.getLogger("intel")


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


def run_analysis(
    db_path,
    ticket_id: str,
    ticket_content: str,
    exec_cmd: str,
    project_root: Path,
    project_id: str | None = None,
) -> None:
    """Run hybrid ticket intelligence analysis and persist the result.

    Designed to run in a background thread. Updates analysis_status through:
    running → completed | failed.
    Never raises — failures are persisted to DB.
    """
    runtime_db.upsert_ticket_intelligence(db_path, ticket_id, analysis_status="running")
    _intel_log.info(
        "intel.started project_id=%s ticket_id=%s db_path=%s",
        project_id, ticket_id, db_path,
    )

    try:
        computed_signals = extract_signals(ticket_content)
        computed_signals_json = json.dumps(computed_signals)

        template = _load_prompt_template(project_root)
        prompt = _fill_template(template, ticket_content, computed_signals_json)

        command = shlex.split(exec_cmd)
        if not command:
            raise ValueError("exec_cmd is empty")

        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        try:
            proc = subprocess.run(
                command,
                input=prompt,
                text=True,
                capture_output=True,
                shell=False,
                check=False,
                env=env,
                timeout=_ANALYSIS_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            _intel_log.info(
                "intel.subprocess project_id=%s ticket_id=%s exec_cmd=%s timeout=%ds rc=timeout",
                project_id, ticket_id, _truncate(exec_cmd, 200), _ANALYSIS_TIMEOUT,
            )
            runtime_db.upsert_ticket_intelligence(
                db_path,
                ticket_id,
                analysis_status="failed",
                analysis_summary="Analysis timed out after 120 seconds.",
                computed_signals_json=computed_signals_json,
            )
            _intel_log.info(
                "intel.failed project_id=%s ticket_id=%s db_path=%s reason=timeout",
                project_id, ticket_id, db_path,
            )
            return

        _intel_log.info(
            "intel.subprocess project_id=%s ticket_id=%s exec_cmd=%s rc=%d stderr=%s",
            project_id, ticket_id, _truncate(exec_cmd, 200), proc.returncode,
            _truncate(proc.stderr, 500),
        )

        if proc.returncode != 0 or not proc.stdout.strip():
            summary = f"AI call failed (rc={proc.returncode})"
            if proc.stderr:
                summary += f": {proc.stderr[:500]}"
            runtime_db.upsert_ticket_intelligence(
                db_path,
                ticket_id,
                analysis_status="failed",
                analysis_summary=summary,
                computed_signals_json=computed_signals_json,
            )
            _intel_log.info(
                "intel.failed project_id=%s ticket_id=%s db_path=%s reason=nonzero_rc rc=%d",
                project_id, ticket_id, db_path, proc.returncode,
            )
            return

        try:
            raw = _extract_json(proc.stdout)
        except ValueError as exc:
            runtime_db.upsert_ticket_intelligence(
                db_path,
                ticket_id,
                analysis_status="failed",
                analysis_summary=f"JSON parse error: {exc}",
                computed_signals_json=computed_signals_json,
            )
            _intel_log.info(
                "intel.failed project_id=%s ticket_id=%s db_path=%s reason=json_parse",
                project_id, ticket_id, db_path,
            )
            return

        normalized = _normalize(raw, computed_signals)

        runtime_db.upsert_ticket_intelligence(
            db_path,
            ticket_id,
            analysis_status="completed",
            computed_signals_json=computed_signals_json,
            **normalized,
        )
        _intel_log.info(
            "intel.completed project_id=%s ticket_id=%s db_path=%s",
            project_id, ticket_id, db_path,
        )

    except Exception as exc:
        runtime_db.upsert_ticket_intelligence(
            db_path,
            ticket_id,
            analysis_status="failed",
            analysis_summary=f"Unexpected error: {exc}",
        )
        _intel_log.info(
            "intel.failed project_id=%s ticket_id=%s db_path=%s reason=exception detail=%s",
            project_id, ticket_id, db_path, _truncate(str(exc), 200),
        )
