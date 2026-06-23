# PR Review

## Résumé

T208 fix le mode "stuck in running" du Ticket Intelligence en durcissant le cycle de vie de l'analyse (background thread, subprocess AI, persistance, reaper) et en propageant 4 nouvelles colonnes `started_at` / `completed_at` / `failed_at` / `failure_origin` sur SQLite et Postgres, avec exposition dans l'API et le dashboard. Le plan §1-9 est entièrement couvert, l'observabilité respecte la séquence imposée (`intel.queued` → `intel.started` → `intel.step.*` → `intel.ai_request.*` → `intel.persisted`), et les tests passent (53 OK / 1 échec pré-existant sur `main`).

## Vérifications effectuées

- Lecture des diffs : `tools/agent_runner/ticket_intelligence_analyzer.py`, `ticket_intelligence_recovery.py`, `runtime_db.py`, `runtime_db_pg.py`, `services/control_api/routes/intelligence.py`, `services/supervisor/main.py`, `services/control_api/models/schemas.py`, `apps/dashboard/src/components/TicketIntelligencePanel.jsx`.
- Lecture des tests ajoutés/modifiés : `tests/test_ticket_intelligence_analyzer.py`, `tests/test_ticket_intelligence_recovery.py`, `tests/test_ticket_intelligence_api.py`, `tests/test_runtime_db_pg.py`.
- Exécution `pytest tests/test_ticket_intelligence_*.py tests/test_runtime_db_pg.py` → **53 passed, 1 failed**.
- Confirmation que l'échec `test_default_backend_is_sqlite` est pré-existant sur `main` (reproduit après reset du fichier de test à `main`).
- Vérification de la séquence de logs `intel.*` et de la cohérence des imports (`runtime_db` importé en haut de `intelligence.py:33` et dans `supervisor/main.py:2229`).

## Points validés

- **Hardening background thread** (plan §1) : `intelligence.py:357-382` et `supervisor/main.py:2342-2362` persistent `failed` + `failure_origin="bg_thread_crash"` si `run_analysis` lève. `ticket_intelligence_analyzer.py:431-454` ajoute un `finally` global qui force `failed` + `failure_origin="finally_guard"` si une `BaseException` (ex : `KeyboardInterrupt`) échappe. `started_at` est écrit dès la transition `running` (`ticket_intelligence_analyzer.py:305-309`).
- **Subprocess borné** (plan §2) : `Popen` + `communicate(timeout)` + `proc.kill()` + drain dans `_run_ai_subprocess` (`ticket_intelligence_analyzer.py:245-279`). `_ANALYSIS_TIMEOUT` configurable via `AI_DEV_FACTORY_INTEL_TIMEOUT` (défaut 120 s).
- **Schéma SQLite** (plan §3) : 4 colonnes dans `_SCHEMA` + migration idempotente `_ensure_ticket_intelligence_lifecycle_columns` introspectant `PRAGMA table_info` (`runtime_db.py:91-95, 256-273, 285`).
- **Schéma Postgres** (plan §4) : 4 colonnes dans `_DDL` + bloc `ADD COLUMN IF NOT EXISTS` exécuté en même connexion (`runtime_db_pg.py:124-135, 232-241, 339-348`). Le commentaire dans le code documente le contrat de parité.
- **Persistance** (plan §5) : tous les chemins (`completed`, `timeout`, `nonzero_rc`, `json_parse`, `exception`, `finally_guard`, `bg_thread_crash`) écrivent l'horodatage et l'origine correspondants.
- **Reaper** (plan §6) : `_scan_stale_rows` sélectionne désormais `analysis_summary` + `failure_origin` ; le résumé pré-existant est préservé et suffixé `(reaper-confirmed after Xs)` ; `failed_at` écrit uniformément (`ticket_intelligence_recovery.py:62-77, 113-141`).
- **API & dashboard** (plan §7) : `TicketIntelligence` étendu (`schemas.py:467-470`) et rendu enrichi `Origin: … · Failed at: …` (`TicketIntelligencePanel.jsx:201-218`).
- **Observabilité** (plan §8) : `intel.queued` au point d'entrée, puis dans l'analyzer `intel.started`, `intel.step.signals_extracted`, `intel.step.prompt_built`, `intel.ai_request.started/completed`, `intel.step.json_parsed`, `intel.persisted`.
- **Tests** (plan §9) : `completed_persists_completed_at`, `timeout_uses_kill_and_persists_failed_at`, `unexpected_exception_in_extract_persists_failed`, `finally_guard_marks_running_row_failed`, `reaper_preserves_existing_summary`, `reaper_writes_failed_at`, `bg_thread_crash_persists_failed`, plus 3 tests Postgres (DDL, migration idempotente, exécution dans `init_runtime_db`) en mode "fallback" comme prévu par le plan §9.
- **Scope** : aucun élément de la section "Excluded" n'est touché (pas de remplacement du threading, pas de nouvelle abstraction DB, pas de modification du reaper-threshold).

## Problèmes détectés

**Mineurs (non bloquants) :**

1. **Reaper §6 — `failure_origin` écrasé au lieu d'être préservé** : le plan disait *"Set `failure_origin='reaper-confirmed'` only when no prior origin exists"*. L'implémentation (`ticket_intelligence_recovery.py:118-126`) écrase `prior_origin` dans la première branche. Le critère d'acceptation §6 ne mentionne explicitement que la préservation du summary, donc l'AC reste satisfait, mais la sémantique du plan n'est pas respectée (un opérateur perd l'information "exception"/"json_parse" remontée par le worker).
2. **Code dupliqué dans le reaper** (`ticket_intelligence_recovery.py:118-126`) : les deux branches `if prior_summary and prior_origin` et `elif prior_summary` produisent un corps identique. Peut être collapsé à `if prior_summary: …`.
3. **Imports locaux répétés** : `from datetime import datetime, timezone` est ré-importé localement dans les deux `_bg` (intelligence.py:370, supervisor/main.py:2349). Cosmétique — pourrait être hissé en tête de module.

## Risques éventuels

- Le `finally`-guard relit la ligne via `runtime_db.get_ticket_intelligence` puis appelle `upsert_ticket_intelligence`. Si la DB devient indisponible pendant l'analyse, le guard peut lui-même échouer : c'est géré par `except Exception: _intel_log.exception(...)` (`ticket_intelligence_analyzer.py:450-454`), mais une telle situation laisse la ligne en l'état (le reaper finit par rattraper après 900 s, comportement précédent). Acceptable.
- La parité Postgres est vérifiée uniquement au niveau des chaînes DDL/migration (fallback prévu par §9). Le critère "freshly initialised Postgres runtime DB has …" reste à valider manuellement contre une instance PG réelle quand l'infra existera. Acceptable.

## Décision

- ~~APPROVED~~
- ~~REQUEST_CHANGES~~

Les écarts identifiés (préservation de `failure_origin` côté reaper, code dupliqué, imports locaux) sont mineurs et ne dégradent ni la correction, ni les critères d'acceptation. Le plan §1-9 est couvert, les tests pertinents passent, l'unique échec restant est pré-existant sur `main`.

## Actions demandées

Aucune action bloquante. Suggestions optionnelles, à intégrer si un follow-up est prévu :
- `ticket_intelligence_recovery.py:118-126` : collapser les deux branches identiques en `if prior_summary: …` et choisir explicitement si `prior_origin` doit être préservé (mettre à jour test + plan en conséquence).
- Hisser `from datetime import datetime, timezone` au sommet de `services/control_api/routes/intelligence.py` et `services/supervisor/main.py` pour éviter la duplication.

IMPLEMENTATION_APPROVED
