"""Tests unitaires pour validate_planner_output()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_step import META_REPORT_REASON, validate_planner_output


def _make_plan(sections: list[str], extra: str = "") -> str:
    body = " word" * 120
    return "\n\n".join(sections) + "\n\n" + body + "\n\n" + extra


CANONICAL_FR = [
    "## contexte",
    "## objectif",
    "## inclus",
    "## hors scope",
    "## critères d'acceptation",
]

SYNONYMS_FR = [
    "## contexte technique",
    "## objectifs",
    "## scope",
    "## non inclus",
    "## acceptance criteria",
]

CANONICAL_EN = [
    "## Context",
    "## Objective",
    "## Included",
    "## Excluded",
    "## Acceptance criteria",
]


def test_valid_canonical_fr():
    assert validate_planner_output(_make_plan(CANONICAL_FR)) == []


def test_valid_synonyms_fr():
    assert validate_planner_output(_make_plan(SYNONYMS_FR)) == []


# ── new bilingual / trivial-ticket tests ─────────────────────────────────────

def test_valid_canonical_en():
    """A full plan with the canonical English headers must pass."""
    assert validate_planner_output(_make_plan(CANONICAL_EN)) == []


def test_valid_small_plan_en():
    """An English plan for a trivial ticket — short but with sections — must pass."""
    plan = (
        "## Objective\n"
        "Rename `foo` to `bar` in `utils.py`. Behaviour-preserving rename.\n\n"
        "## Included\n"
        "- utils.py\n\n"
        "## Excluded\n"
        "- callers\n\n"
        "## Acceptance criteria\n"
        "- module still imports, tests green"
    )
    assert validate_planner_output(plan) == []


def test_valid_small_plan_fr():
    """A French plan for a trivial ticket — short but with sections — must pass."""
    plan = (
        "## Objectif\n"
        "Renommer `foo` en `bar` dans `utils.py`. Renommage préservant le comportement.\n\n"
        "## Inclus\n"
        "- utils.py\n\n"
        "## Hors scope\n"
        "- appelants\n\n"
        "## Critères d'acceptation\n"
        "- import OK, tests verts"
    )
    assert validate_planner_output(plan) == []


def test_empty_plan_is_rejected():
    """An empty / whitespace-only plan must be rejected."""
    reasons = validate_planner_output("   \n  \n")
    assert reasons, "empty plan must be rejected"


def test_garbage_one_liner_is_rejected():
    """A one-line throwaway answer with no structure must be rejected."""
    reasons = validate_planner_output("done")
    assert any("trop court" in r and "sans section reconnue" in r for r in reasons)


def test_long_prose_without_section_still_rejected():
    """Removing the word-count short-circuit must NOT let unstructured prose pass."""
    plan = (
        "Je vais modifier le fichier utils.py et renommer la variable foo en bar. "
        "Ensuite je mets à jour les tests pour refléter ce changement et je relance "
        "la suite complète. Si tout passe je crée la PR et je demande une review."
    ) * 3
    reasons = validate_planner_output(plan)
    assert any("section reconnue" in r for r in reasons)


# ── tests historiques (adaptés au nouveau comportement) ──────────────────────

def test_missing_section_is_not_blocking_anymore():
    """Avoir 4/5 sections reste OK — au moins une section suffit."""
    sections = [s for s in CANONICAL_FR if "hors scope" not in s]
    reasons = validate_planner_output(_make_plan(sections))
    assert reasons == []


def test_forbidden_phrase_real():
    plan = _make_plan(CANONICAL_FR, extra="implémentation terminée")
    reasons = validate_planner_output(plan)
    assert any("phrase interdite" in r for r in reasons)


def test_forbidden_phrase_in_code_block():
    plan = _make_plan(CANONICAL_FR, extra="```\nimplémentation terminée\n```")
    assert validate_planner_output(plan) == []


def test_small_plan_with_one_section_passes():
    """Tickets triviaux: un petit plan avec au moins une section reconnue est OK."""
    plan = (
        "## Objectif\n"
        "Renommer la variable foo en bar dans le module utils. "
        "Pas de changement de comportement, juste une homogénéisation."
    )
    assert validate_planner_output(plan) == []


def test_plan_without_any_section_is_rejected():
    """Un plan sans aucune section reconnue est rejeté (probablement pas un plan)."""
    plan = (
        "Voici une réponse libre sans aucune structure de plan: "
        "on va modifier le fichier et tout devrait fonctionner correctement, "
        "il suffit de remplacer la chaîne de caractères concernée par la nouvelle valeur."
    )
    reasons = validate_planner_output(plan)
    assert any("section reconnue" in r for r in reasons)


# ── meta-report heuristic (T202) ─────────────────────────────────────────────

def test_hard_meta_report_plan_written_to_is_rejected():
    """Claude Code often Writes the real plan then prints this chatty summary."""
    meta_report = (
        "Plan written to `runs/T035/plan.md`. Key decisions made from "
        "codebase exploration:\n\n"
        "- **No routing library** — scope creep.\n"
        "- **New `AppShell.tsx`** component.\n"
        "- Targeting `docs/frontend-audit.md`.\n"
    )
    reasons = validate_planner_output(meta_report)
    assert META_REPORT_REASON in reasons


def test_hard_meta_report_runs_path_is_written_is_rejected():
    meta_report = (
        "`runs/T033/plan.md` is written. The plan covers:\n\n"
        "- **Two inspectable views** (`selector` and `history`).\n"
        "- Targeting `docs/frontend-audit.md`.\n"
    )
    reasons = validate_planner_output(meta_report)
    assert META_REPORT_REASON in reasons


def test_resolve_exec_output_prefers_valid_disk_over_meta_stdout(tmp_path, monkeypatch):
    """When the agent Write()s a valid plan then prints a meta-report, keep disk."""
    from run_step import resolve_exec_output_content

    monkeypatch.chdir(tmp_path)
    plan_path = tmp_path / "runs" / "T099" / "plan.md"
    plan_path.parent.mkdir(parents=True)
    valid = (
        "## Objective\n"
        "Configure Vite host binding for LAN access.\n\n"
        "## Included\n"
        "- `frontend/vite.config.ts`: server.host 0.0.0.0\n\n"
        "## Excluded\n"
        "- Production deploy.\n\n"
        "## Acceptance criteria\n"
        "- `npm run dev` binds 0.0.0.0:5173\n"
    )
    plan_path.write_text(valid)
    meta = "`runs/T099/plan.md` is written. The plan covers LAN access."
    chosen = resolve_exec_output_content("planner", plan_path, meta)
    assert chosen == valid


def test_resolve_exec_output_keeps_stdout_when_disk_invalid(tmp_path, monkeypatch):
    from run_step import resolve_exec_output_content

    monkeypatch.chdir(tmp_path)
    plan_path = tmp_path / "runs" / "T099" / "plan.md"
    plan_path.parent.mkdir(parents=True)
    plan_path.write_text("garbage")
    stdout = (
        "## Objective\n"
        "Do the thing.\n\n"
        "## Included\n"
        "- a.py\n\n"
        "## Excluded\n"
        "- b.py\n\n"
        "## Acceptance criteria\n"
        "- tests pass\n"
    )
    assert resolve_exec_output_content("planner", plan_path, stdout) == stdout


def test_meta_report_t201_repro_is_rejected():
    """Reproduces the T201 failure mode: the planner returns a status report
    about its own work instead of the plan artifact itself."""
    meta_report = (
        "The plan has been rewritten to be a real implementation document. "
        "Key points covered include the objective, the scope, the exclusions "
        "and the acceptance criteria. The plan now contains a clear set of "
        "steps that the coder can follow. Plan rewritten as a real "
        "implementation document."
    )
    reasons = validate_planner_output(meta_report)
    assert META_REPORT_REASON in reasons


def test_meta_report_after_summary_heading_is_rejected():
    """A meta-report wrapped under a non-canonical heading (no real
    structure, no bullet list, no paths, no code) must still be rejected
    by the meta-report heuristic."""
    meta_report = (
        "## Summary\n\n"
        "The plan has been rewritten to ensure that the acceptance criteria "
        "are now clearer and the scope is well delimited. "
        "Key points covered include refactor of utilities and renaming."
    )
    reasons = validate_planner_output(meta_report)
    assert META_REPORT_REASON in reasons


def test_meta_report_phrase_inside_structured_plan_is_not_rejected():
    """Counter-test: a structured plan that *contains* a meta-report-like
    sentence inside one of its sections must still pass — no false positive."""
    plan = (
        "## Objective\n"
        "Rename `foo` to `bar` in `utils.py`. The plan now ensures behaviour "
        "is preserved across the refactor.\n\n"
        "## Included\n"
        "- utils.py: rename `foo` to `bar`.\n"
        "- tests/test_utils.py: update the assertion.\n\n"
        "## Excluded\n"
        "- callers in other modules.\n\n"
        "## Acceptance criteria\n"
        "- tests pass; the module no longer exports `foo`."
    )
    assert validate_planner_output(plan) == []


def test_meta_report_with_bullets_is_not_rejected():
    """A plan opening with 'The plan now…' but carrying a real bullet list
    of changes is not a meta-report."""
    plan = (
        "## Objectif\n"
        "The plan now covers the full migration in a single step.\n\n"
        "## Inclus\n"
        "- step 1: switch the config flag\n"
        "- step 2: deploy and observe metrics\n\n"
        "## Critères d'acceptation\n"
        "- metric stays green for 24h"
    )
    reasons = validate_planner_output(plan)
    assert META_REPORT_REASON not in reasons


def test_artifact_type_default_is_plan():
    """The new ``artifact_type`` parameter must default to ``"plan"`` and
    preserve existing behaviour for callers that do not pass it."""
    plan = (
        "## Objective\n"
        "Rename `foo` to `bar`.\n\n"
        "## Included\n"
        "- utils.py\n\n"
        "## Excluded\n"
        "- callers\n\n"
        "## Acceptance criteria\n"
        "- tests pass"
    )
    assert validate_planner_output(plan) == validate_planner_output(plan, artifact_type="plan")
