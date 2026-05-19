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

## 2026-05-19 — T114 — Séparation clone humain / clone runtime

Architecture runtime officielle définie et documentée.

Séparation stricte introduite entre clone humain (développement) et clone runtime (daemon + agents).
Le daemon refuse de démarrer dans un clone humain via `_check_runtime_clone()` (sentinel `.ai-dev-factory-runtime` ou env var `AI_DEV_FACTORY_RUNTIME_ROOT`).

Structure cible : `~/runtime/ai-dev-factory/{clones,worktrees,state,logs}`.
Migration effective des chemins actuels : hors scope T114, fera l'objet d'un ticket dédié.

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
