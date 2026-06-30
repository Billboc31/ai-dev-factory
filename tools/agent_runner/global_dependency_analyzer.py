"""Global Dependency Analyzer (T218).

Runs a single AI subprocess on a *whole* frozen backlog batch and persists
per-ticket dependency rows into ``ticket_dependency_analysis`` (UPSERT, safe
to retry). Pure I/O around the analyzer: the batch lifecycle state machine
lives in :mod:`backlog_batch`, the AI invocation pattern mirrors
``ticket_intelligence_analyzer``.

The entry point :func:`run_global_analysis` never raises. Failures (timeout,
non-zero rc, malformed JSON) are reported as
``AnalysisOutcome(success=False, error=…)`` so the daemon can drive the
retry/cooldown/max-attempts policy via ``backlog_batch``.
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
from dataclasses import dataclass
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402


logger = logging.getLogger("global_dependency_analyzer")

_VALID_RELATIONSHIP_TYPES = frozenset({
    "HARD_DEPENDENCY",
    "SOFT_DEPENDENCY",
    "FOUNDATION_DEPENDENCY",
    "PARALLEL_COMPATIBLE",
    "CONFLICTING_SCOPE",
})


@dataclass
class AnalysisOutcome:
    success: bool
    error: str | None = None
    persisted_ticket_count: int = 0


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


_INLINE_PROMPT = """\
You are a Global Dependency Analyzer for an AI-assisted software development system.

Analyse the following batch of tickets *together* and return ONLY a JSON object.
Do not include any explanation, markdown, or text outside the JSON object.

## Batch tickets

{{batch_tickets}}

## Required JSON output

Return exactly this structure:

```json
{
  "tickets": [
    {
      "ticket_id": "T011",
      "depends_on": ["T010"],
      "blocks": [],
      "parallel_group": "foundation",
      "conflicting_tickets": [],
      "execution_phase": 1
    }
  ],
  "relationships": [
    { "from": "T011", "to": "T010", "type": "HARD_DEPENDENCY" }
  ]
}
```

``type`` must be one of: HARD_DEPENDENCY, SOFT_DEPENDENCY, FOUNDATION_DEPENDENCY,
PARALLEL_COMPATIBLE, CONFLICTING_SCOPE.
"""


_TEMPLATE_VARS_RE = re.compile(r"\{\{(batch_tickets)\}\}")


def _fill_template(template: str, batch_tickets_text: str) -> str:
    values = {"batch_tickets": batch_tickets_text}
    return _TEMPLATE_VARS_RE.sub(lambda m: values.get(m.group(1), m.group(0)), template)


def _load_prompt_template(project_root: Path) -> str:
    prompt_path = project_root / "prompts" / "global-dependency-analyzer-prompt.md"
    if prompt_path.exists():
        try:
            return prompt_path.read_text(encoding="utf-8")
        except OSError:
            pass
    return _INLINE_PROMPT


def _decode_hints(raw_hints) -> list[str]:
    if raw_hints is None:
        return []
    if isinstance(raw_hints, str):
        try:
            decoded = json.loads(raw_hints)
        except json.JSONDecodeError:
            return []
    else:
        decoded = raw_hints
    if not isinstance(decoded, list):
        return []
    return [str(h) for h in decoded if isinstance(h, (str, int))]


def _build_batch_section(
    db_path,
    runs_dir: Path,
    ticket_ids: list[str],
) -> str:
    """Build the human-readable batch section embedded into the prompt."""
    sections: list[str] = []
    for ticket_id in ticket_ids:
        ticket_md = ""
        candidate = runs_dir / ticket_id / "ticket.md"
        if candidate.is_file():
            try:
                ticket_md = candidate.read_text(encoding="utf-8")
            except OSError:
                ticket_md = ""
        intel = None
        try:
            intel = runtime_db.get_ticket_intelligence(db_path, ticket_id)
        except Exception:
            intel = None
        summary = (intel or {}).get("analysis_summary") or ""
        hints = _decode_hints((intel or {}).get("dependency_hints"))
        sections.append(
            f"### {ticket_id}\n"
            f"intelligence_summary: {summary}\n"
            f"dependency_hints: {hints}\n"
            f"ticket_markdown:\n{ticket_md}\n"
        )
    return "\n---\n".join(sections)


def _run_ai_subprocess(
    command: list[str],
    prompt: str,
    env: dict,
    timeout: int,
    *,
    cwd: Path | str | None = None,
) -> tuple[int, str, str, bool, int]:
    """Run the AI subprocess with an enforced upper bound on wall-clock time."""
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


def _coerce_str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            out.append(item.strip())
    return out


def _coerce_execution_phase(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _normalize_response(raw: dict) -> tuple[list[dict], list[dict]]:
    tickets = raw.get("tickets")
    relationships = raw.get("relationships") or []

    if not isinstance(tickets, list):
        raise ValueError("missing or non-list 'tickets'")
    if not isinstance(relationships, list):
        relationships = []

    norm_tickets: list[dict] = []
    for entry in tickets:
        if not isinstance(entry, dict):
            continue
        tid = entry.get("ticket_id")
        if not isinstance(tid, str) or not tid.strip():
            continue
        norm_tickets.append({
            "ticket_id": tid.strip(),
            "depends_on": _coerce_str_list(entry.get("depends_on")),
            "blocks": _coerce_str_list(entry.get("blocks")),
            "parallel_group": (
                entry.get("parallel_group").strip()
                if isinstance(entry.get("parallel_group"), str)
                and entry.get("parallel_group").strip()
                else None
            ),
            "conflicting_tickets": _coerce_str_list(entry.get("conflicting_tickets")),
            "execution_phase": _coerce_execution_phase(entry.get("execution_phase")),
        })

    norm_relationships: list[dict] = []
    for rel in relationships:
        if not isinstance(rel, dict):
            continue
        rtype = rel.get("type")
        rfrom = rel.get("from")
        rto = rel.get("to")
        if not (
            isinstance(rtype, str)
            and rtype in _VALID_RELATIONSHIP_TYPES
            and isinstance(rfrom, str)
            and isinstance(rto, str)
        ):
            continue
        norm_relationships.append({"from": rfrom, "to": rto, "type": rtype})

    return norm_tickets, norm_relationships


def _persist(
    db_path,
    batch_id: str,
    norm_tickets: list[dict],
    norm_relationships: list[dict],
    *,
    now: str,
) -> int:
    """Persist per-ticket rows via UPSERT. Returns the number of rows written."""
    rels_by_from: dict[str, list[dict]] = {}
    for rel in norm_relationships:
        rels_by_from.setdefault(rel["from"], []).append(rel)

    persisted = 0
    for entry in norm_tickets:
        runtime_db.upsert_dependency_analysis(
            db_path,
            ticket_id=entry["ticket_id"],
            batch_id=batch_id,
            depends_on=entry["depends_on"],
            blocks=entry["blocks"],
            parallel_group=entry["parallel_group"],
            conflicting_tickets=entry["conflicting_tickets"],
            execution_phase=entry["execution_phase"],
            relationship_classifications=rels_by_from.get(entry["ticket_id"], []),
            analyzed_at=now,
        )
        persisted += 1
    return persisted


def run_global_analysis(
    db_path,
    runs_dir: Path,
    batch_id: str,
    *,
    exec_cmd: str,
    timeout_seconds: int = 240,
    project_root: Path | None = None,
) -> AnalysisOutcome:
    """Run the global dependency analyzer for one batch and persist rows.

    Never raises. Persisted rows survive retries (UPSERT). On success returns
    ``AnalysisOutcome(success=True, persisted_ticket_count=N)``; otherwise
    ``AnalysisOutcome(success=False, error=…)``.
    """
    runs_dir = Path(runs_dir)
    project_root = Path(project_root) if project_root is not None else runs_dir.parent
    try:
        ticket_ids = runtime_db.list_backlog_batch_ticket_ids(db_path, batch_id)
    except Exception as exc:
        return AnalysisOutcome(success=False, error=f"db error listing tickets: {exc}")
    if not ticket_ids:
        return AnalysisOutcome(success=False, error="batch has no tickets")

    try:
        batch_section = _build_batch_section(db_path, runs_dir, ticket_ids)
    except Exception as exc:
        return AnalysisOutcome(success=False, error=f"failed to build batch section: {exc}")

    template = _load_prompt_template(project_root)
    prompt = _fill_template(template, batch_section)

    try:
        command = shlex.split(exec_cmd)
    except ValueError as exc:
        return AnalysisOutcome(success=False, error=f"invalid exec_cmd: {exc}")
    if not command:
        return AnalysisOutcome(success=False, error="exec_cmd is empty")
    if "--print" not in command and "-p" not in command:
        command = command + ["--print"]

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    try:
        rc, stdout, stderr, timed_out, _ = _run_ai_subprocess(
            command, prompt, env, timeout_seconds, cwd=project_root,
        )
    except Exception as exc:
        return AnalysisOutcome(success=False, error=f"subprocess error: {exc}")

    if timed_out:
        return AnalysisOutcome(success=False, error=f"timeout after {timeout_seconds}s")
    if rc != 0:
        detail = (stderr or stdout or "").strip()[:500]
        return AnalysisOutcome(success=False, error=f"non-zero rc={rc}: {detail}")
    if not stdout.strip():
        return AnalysisOutcome(success=False, error="empty stdout")

    try:
        raw = _extract_json(stdout)
    except ValueError as exc:
        return AnalysisOutcome(success=False, error=f"malformed JSON: {exc}")

    try:
        norm_tickets, norm_relationships = _normalize_response(raw)
    except ValueError as exc:
        return AnalysisOutcome(success=False, error=f"invalid response shape: {exc}")

    try:
        persisted = _persist(
            db_path, batch_id, norm_tickets, norm_relationships, now=_now_iso(),
        )
    except Exception as exc:
        return AnalysisOutcome(success=False, error=f"persist failed: {exc}")

    return AnalysisOutcome(success=True, persisted_ticket_count=persisted)


__all__ = [
    "AnalysisOutcome",
    "run_global_analysis",
]
