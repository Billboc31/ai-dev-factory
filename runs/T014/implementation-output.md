Les permissions d'écriture sur `run_step.py` ne sont pas accordées dans l'UI. Veuillez approuver l'accès en écriture à ce fichier (et idéalement au répertoire `tests/` pour le fichier de test). 

En attendant, voici les diffs complets pour revue :

---

**Diff 1 — `tools/agent_runner/run_step.py` : `_REQUIRED_SECTION_GROUPS`**

```diff
 _REQUIRED_SECTION_GROUPS = {
-    "contexte": ["## contexte", "## diagnostic", "## contexte et diagnostic"],
+    "contexte": ["## contexte", "## diagnostic", "## contexte et diagnostic", "## contexte technique"],
     "objectif": ["## objectif", "## objectifs", "## but"],
     "inclus": [
         "## inclus",
         "## périmètre",
         "## scope",
         "## changements prévus",
         "## plan",
         "## étapes",
         "## étapes d'implémentation",
-        "## étapes d'implémentation",
     ],
     "hors scope": ["## hors scope", "## hors périmètre", "## non inclus", "## exclusions"],
     "critères d'acceptation": [
         "## critères d'acceptation",
         "## critères",
         "## validation",
         "## critères de validation",
+        "## acceptance criteria",
     ],
 }
```

---

**Diff 2 — `tools/agent_runner/run_step.py` : `validate_planner_output()` (lignes 275–277)**

```diff
+    # Strip code fences and inline code before checking forbidden phrases
+    # to avoid false positives when a plan cites guard phrases as examples.
+    code_stripped = re.sub(r"```[\s\S]*?```", "", lower)
+    code_stripped = re.sub(r"`[^`\n]+`", "", code_stripped)
+
     for phrase in _FORBIDDEN_PHRASES:
-        if phrase in lower:
+        if phrase in code_stripped:
             reasons.append(f"phrase interdite: «{phrase}»")
```

---

**Diff 3 — `tests/test_validate_planner_output.py` (nouveau fichier)**

```python
"""Tests unitaires pour validate_planner_output()."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_step import validate_planner_output


def _make_plan(sections: list[str], extra: str = "") -> str:
    body = " word" * 120
    return "\n\n".join(sections) + "\n\n" + body + "\n\n" + extra


CANONICAL = [
    "## contexte",
    "## objectif",
    "## inclus",
    "## hors scope",
    "## critères d'acceptation",
]

SYNONYMS = [
    "## contexte technique",
    "## objectifs",
    "## scope",
    "## non inclus",
    "## acceptance criteria",
]


def test_valid_canonical():
    assert validate_planner_output(_make_plan(CANONICAL)) == []


def test_valid_synonyms():
    assert validate_planner_output(_make_plan(SYNONYMS)) == []


def test_too_short():
    short = "\n\n".join(CANONICAL) + "\n\ncourt"
    reasons = validate_planner_output(short)
    assert any("plan trop court" in r for r in reasons)


def test_missing_section():
    sections = [s for s in CANONICAL if "hors scope" not in s]
    reasons = validate_planner_output(_make_plan(sections))
    assert any("hors scope" in r for r in reasons)


def test_forbidden_phrase_real():
    plan = _make_plan(CANONICAL, extra="implémentation terminée")
    reasons = validate_planner_output(plan)
    assert any("phrase interdite" in r for r in reasons)


def test_forbidden_phrase_in_code_block():
    # A plan that cites a forbidden phrase inside a code fence must not be rejected.
    plan = _make_plan(CANONICAL, extra="```\nimplémentation terminée\n```")
    assert validate_planner_output(plan) == []
```

---

Une fois que vous approuvez l'écriture dans l'UI, je peux appliquer ces 3 changements et lancer les tests.
