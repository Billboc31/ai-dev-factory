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

## How to reason

Think like a software architect planning the whole batch:

1. First, build a conceptual implementation plan by grouping tickets into
   layers: foundation/bootstrap (vision, architecture, tech stack,
   conventions, scaffolding), then infrastructure, then backend APIs, then
   frontend / UI, then features, then integration, then quality/testing.
2. Only then derive ``depends_on`` / ``blocks`` / ``parallel_group`` /
   ``conflicting_tickets`` / ``execution_phase`` and the ``relationships``
   array from that plan.

Foundation tickets — those defining product vision, overall architecture,
technical stack, conventions, or project bootstrap/scaffolding — belong in
the earliest execution phases. Prefer classifying dependencies whose target
is a foundation ticket as ``FOUNDATION_DEPENDENCY``.

Infer implicit architectural dependencies even when tickets do not cite each
other by id: architecture → bootstrap, bootstrap → backend/frontend
foundations, backend API → frontend consuming it, infrastructure → features,
features → integration, implementation → testing.

## Output invariants

The final JSON output MUST satisfy these invariants:

1. Phase ordering: if ticket A lists B in ``depends_on``, then
   ``execution_phase(A) > execution_phase(B)``.
2. Same-phase parallelism: tickets sharing an ``execution_phase`` must be
   parallel-compatible.
3. Conflict exclusivity: if B is in A.conflicting_tickets, then
   ``execution_phase(A) != execution_phase(B)``.
4. Foundation position: foundation/bootstrap tickets occupy the earliest
   phase(s).

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


# ── Coherence pass ────────────────────────────────────────────────────────────

ROLE_ORDER = (
    "FOUNDATION",
    "BOOTSTRAP",
    "INFRASTRUCTURE",
    "BACKEND_API",
    "FRONTEND_UI",
    "FEATURE",
    "INTEGRATION",
    "QUALITY_TESTING",
    "DOCS_MISC",
    "UNKNOWN",
)

_ROLE_PATTERNS: tuple[tuple[str, re.Pattern], ...] = (
    ("FOUNDATION", re.compile(
        r"architecture|vision|stack|conventions|foundation|global context",
        re.IGNORECASE,
    )),
    ("BOOTSTRAP", re.compile(
        r"bootstrap|scaffold|initial setup|project foundation",
        re.IGNORECASE,
    )),
    ("BACKEND_API", re.compile(
        r"backend|api|endpoint|route|service",
        re.IGNORECASE,
    )),
    ("FRONTEND_UI", re.compile(
        r"frontend|ui|page|react|dashboard|component",
        re.IGNORECASE,
    )),
    ("QUALITY_TESTING", re.compile(
        r"test|playwright|regression|coverage|qa",
        re.IGNORECASE,
    )),
    ("INTEGRATION", re.compile(
        r"integration|wiring|end-to-end|connect",
        re.IGNORECASE,
    )),
    ("INFRASTRUCTURE", re.compile(
        r"infra|infrastructure|deployment|\bci\b|\bcd\b|pipeline",
        re.IGNORECASE,
    )),
    ("DOCS_MISC", re.compile(
        r"docs|documentation|readme|typo",
        re.IGNORECASE,
    )),
)


def _infer_ticket_role(
    ticket_id: str,
    ticket_text: str,
    relationships: list[dict],
    has_dependency_signal: bool,
) -> str:
    """Infer an architectural role for a ticket from its text + relationships."""
    for rel in relationships:
        if rel.get("type") == "FOUNDATION_DEPENDENCY" and rel.get("to") == ticket_id:
            return "FOUNDATION"
    text = ticket_text or ""
    for role, pattern in _ROLE_PATTERNS:
        if pattern.search(text):
            return role
    if has_dependency_signal:
        return "FEATURE"
    return "UNKNOWN"


def _topological_order(deps: dict[str, set[str]]) -> list[str]:
    """DFS-based topological order; deps come before dependents. Assumes DAG."""
    order: list[str] = []
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        visited.add(node)
        for d in sorted(deps.get(node, set())):
            if d in deps:
                visit(d)
        order.append(node)

    for t in sorted(deps.keys()):
        visit(t)
    return order


def _break_cycles(deps: dict[str, set[str]]) -> int:
    """Remove back-edges via DFS coloring to make the graph acyclic.

    Returns the count of removed edges. Mutates ``deps`` in place.
    """
    removed = 0
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {t: WHITE for t in deps}

    def visit(node: str) -> None:
        nonlocal removed
        color[node] = GRAY
        for d in sorted(list(deps.get(node, set()))):
            state = color.get(d, WHITE)
            if state == GRAY:
                deps[node].discard(d)
                removed += 1
            elif state == WHITE and d in deps:
                visit(d)
        color[node] = BLACK

    for t in sorted(list(deps.keys())):
        if color[t] == WHITE:
            visit(t)
    return removed


def _compute_phases(
    deps: dict[str, set[str]],
    ticket_ids: list[str],
    forced_min: dict[str, int],
) -> dict[str, int]:
    """Longest-path phase assignment. ``forced_min[t]`` is an extra lower bound."""
    order = _topological_order(deps)
    phases: dict[str, int] = {}
    for t in order:
        base = 1
        if deps.get(t):
            dep_phases = [phases[d] for d in deps[t] if d in phases]
            if dep_phases:
                base = 1 + max(dep_phases)
        phases[t] = max(base, forced_min.get(t, 1))
    for t in ticket_ids:
        phases.setdefault(t, max(1, forced_min.get(t, 1)))
    return phases


def _transitively_depends(a: str, b: str, deps: dict[str, set[str]]) -> bool:
    """True if ``a`` transitively depends on ``b``."""
    seen: set[str] = set()
    stack: list[str] = list(deps.get(a, set()))
    while stack:
        node = stack.pop()
        if node == b:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(deps.get(node, set()))
    return False


def _resolve_conflict_pair(
    a: str,
    b: str,
    deps: dict[str, set[str]],
    roles: dict[str, str],
    original_phases: dict[str, int],
) -> tuple[str, str]:
    """Pick which ticket in a same-phase conflict to bump.

    Returns ``(ticket_to_bump, resolver_step)``. ``resolver_step`` is one of
    ``dependency`` / ``role`` / ``original_phase`` / ``ticket_id``.
    """
    if _transitively_depends(a, b, deps):
        return a, "dependency"
    if _transitively_depends(b, a, deps):
        return b, "dependency"

    a_idx = ROLE_ORDER.index(roles.get(a, "UNKNOWN"))
    b_idx = ROLE_ORDER.index(roles.get(b, "UNKNOWN"))
    if a_idx != b_idx:
        return (b, "role") if a_idx < b_idx else (a, "role")

    a_orig = original_phases.get(a, 0)
    b_orig = original_phases.get(b, 0)
    if a_orig != b_orig:
        return (a, "original_phase") if a_orig > b_orig else (b, "original_phase")

    return (a, "ticket_id") if a > b else (b, "ticket_id")


def _enforce_coherence(
    norm_tickets: list[dict],
    norm_relationships: list[dict],
    original_phases: dict[str, int],
    ticket_texts: dict[str, str] | None = None,
) -> tuple[list[dict], list[dict], list[str]]:
    """Post-process the analyzer response so the output invariants hold.

    Fixes the graph deterministically rather than failing:

    - Enforces ``phase(A) > phase(B)`` whenever ``A depends_on B`` via a
      topological longest-path pass.
    - Detects and breaks dependency cycles (drops back-edges).
    - Splits same-phase conflicting pairs using a priority ladder:
      dependency direction → role ordering → original LLM phase → ticket id.
    """
    ticket_texts = ticket_texts or {}
    notes: list[str] = []
    ticket_ids = [t["ticket_id"] for t in norm_tickets]
    ticket_set = set(ticket_ids)

    deps: dict[str, set[str]] = {}
    for t in norm_tickets:
        tid = t["ticket_id"]
        deps[tid] = {
            d for d in t["depends_on"] if d in ticket_set and d != tid
        }

    cycles_broken = _break_cycles(deps)
    if cycles_broken:
        notes.append(f"cycles_broken={cycles_broken}")

    roles: dict[str, str] = {}
    for tid in ticket_ids:
        roles[tid] = _infer_ticket_role(
            tid,
            ticket_texts.get(tid, ""),
            norm_relationships,
            has_dependency_signal=bool(deps.get(tid)),
        )

    conflicting_map: dict[str, set[str]] = {}
    for t in norm_tickets:
        tid = t["ticket_id"]
        conflicting_map[tid] = {
            c for c in t["conflicting_tickets"] if c in ticket_set and c != tid
        }

    forced_min: dict[str, int] = {}
    phases = _compute_phases(deps, ticket_ids, forced_min)
    original_int_phases = dict(phases)  # snapshot in case we need it later

    resolver_steps: list[str] = []
    conflict_splits = 0
    max_iters = len(ticket_ids) * 4 + 10
    for _ in range(max_iters):
        collisions: list[tuple[str, str]] = []
        seen_pairs: set[tuple[str, str]] = set()
        for tid, cts in conflicting_map.items():
            for other in cts:
                if other not in ticket_set:
                    continue
                pair = (tid, other) if tid < other else (other, tid)
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                if phases[pair[0]] == phases[pair[1]]:
                    collisions.append(pair)
        if not collisions:
            break
        for a, b in collisions:
            bump, step = _resolve_conflict_pair(
                a, b, deps, roles, original_phases,
            )
            resolver_steps.append(step)
            conflict_splits += 1
            keep = b if bump == a else a
            forced_min[bump] = max(
                forced_min.get(bump, 0), phases[keep] + 1,
            )
        phases = _compute_phases(deps, ticket_ids, forced_min)

    phase_reassignments = 0
    for t in norm_tickets:
        tid = t["ticket_id"]
        new_phase = str(phases[tid])
        old_phase = t.get("execution_phase")
        if old_phase != new_phase:
            phase_reassignments += 1
        t["execution_phase"] = new_phase
        t["depends_on"] = sorted(deps[tid])

    if resolver_steps or phase_reassignments or cycles_broken:
        logger.info(
            "global_dependency_analyzer coherence: "
            "phase_reassignments=%d cycles_broken=%d conflict_splits=%d "
            "resolver_steps=%s",
            phase_reassignments,
            cycles_broken,
            conflict_splits,
            resolver_steps,
        )
    notes.append(f"phase_reassignments={phase_reassignments}")
    notes.append(f"conflict_splits={conflict_splits}")
    notes.append(f"resolver_steps={resolver_steps}")

    # Silence unused warning; kept for future debug hooks
    _ = original_int_phases

    return norm_tickets, norm_relationships, notes


def _load_ticket_texts(runs_dir: Path, ticket_ids: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for tid in ticket_ids:
        candidate = runs_dir / tid / "ticket.md"
        if candidate.is_file():
            try:
                out[tid] = candidate.read_text(encoding="utf-8")
            except OSError:
                out[tid] = ""
        else:
            out[tid] = ""
    return out


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

    original_phases: dict[str, int] = {}
    for entry in norm_tickets:
        raw_phase = entry.get("execution_phase")
        try:
            original_phases[entry["ticket_id"]] = (
                int(raw_phase) if raw_phase is not None else 0
            )
        except (TypeError, ValueError):
            original_phases[entry["ticket_id"]] = 0

    ticket_texts = _load_ticket_texts(runs_dir, ticket_ids)

    try:
        norm_tickets, norm_relationships, _coherence_notes = _enforce_coherence(
            norm_tickets, norm_relationships, original_phases, ticket_texts,
        )
    except Exception as exc:
        logger.warning("coherence pass failed; persisting raw output: %s", exc)

    try:
        persisted = _persist(
            db_path, batch_id, norm_tickets, norm_relationships, now=_now_iso(),
        )
    except Exception as exc:
        return AnalysisOutcome(success=False, error=f"persist failed: {exc}")

    return AnalysisOutcome(success=True, persisted_ticket_count=persisted)


__all__ = [
    "AnalysisOutcome",
    "ROLE_ORDER",
    "_enforce_coherence",
    "_infer_ticket_role",
    "_resolve_conflict_pair",
    "run_global_analysis",
]
