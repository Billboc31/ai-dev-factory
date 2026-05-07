# Decisions log — ai-dev-factory

Décisions structurantes datées. Les détails opérationnels vivent dans `docs/ai/project-life.md` et les documents référencés.

---

## 2026-05-07 — T002 — Document canonique lifecycle PR et artefacts `runs/`

Standardisation du lifecycle PR IA et de l’arborescence `runs/TXXX/`.

---

## 2026-05-07 — T003 — Agent local minimal volontairement non autonome

Création du runner local minimal `run_step.py` sans autonomie ni appels API LLM.

---

## 2026-05-07 — T005 — Exécution externe contrôlée

Le runner Python reste orchestrateur principal.
Les moteurs externes (Claude CLI, Codex CLI, etc.) génèrent uniquement du contenu via stdin/stdout.

---

## 2026-05-07 — T007 — Workflow Git ticket branch

Adoption de la convention Git :

`ticket/TXXX-*`

Le runner local peut désormais :
- créer/switch une branche ticket
- commit explicitement les changements
- push explicitement une branche

Le système reste volontairement non autonome :
- pas de merge automatique
- pas de PR automatique
- pas de review distante automatique
