Le plan est écrit dans `runs/T107/plan.md`. Voici un résumé de ce qui a été produit :

---

## Plan T107 — Résumé

**5 couches à implémenter :**

1. **`.ai-dev-factory/project.yml`** — Config projet (services, healthchecks, checks, smoke tests)

2. **`tools/guardian/`** — 9 modules :
   - `project_profile.py` — charge/valide le YAML
   - `sandbox_manager.py` — clone temporaire (`--depth 1`), context manager avec cleanup garanti
   - `service_runner.py` — start/stop services, poll healthchecks via httpx
   - `check_runner.py` — run séquentiel des checks, capture exit code + output
   - `mock_agent.py` — fake LLM pour smoke tests (lit le prompt, émet PLAN_APPROVED/IMPLEMENTATION_APPROVED/TEST_COMPLETE)
   - `smoke_runner.py` — mode Playwright + mode runtime workflow mock (désactivé par défaut)
   - `issue_reporter.py` — `gh issue create` avec labels `ai-ready`, `regression`, severity
   - `guardian_core.py` — orchestration complète + persistence dans `runs/guardian/YYYYMMDD-HHMMSS/`
   - `run_guardian.py` — CLI (`--no-sandbox`, `--checks-only`, `--no-smoke`, `--trigger`)

3. **API backend** — `GET /guardian/status`, `GET /guardian/runs`, `POST /guardian/run`

4. **Dashboard** — `ProjectHealthPage.jsx` (dernier scan, build status, régressions, bouton "Run now")

5. **Tests** — 3 fichiers couvrant profile loader, core orchestration, issue reporter

**Risques principaux :** conflits de ports, `gh` non authentifié, smoke runtime instable (désactivé par défaut).

**Hors scope V1 :** auto-revert, auto-fix, GitHub Actions, cron/schedule, trigger automatique post-merge, graphes de tendance.
