---

# PR Review — T025 — Daemon retry and cooldown policy

## Résumé

Implémentation de la politique de retry/cooldown dans `run_daemon.py`. Deux fichiers modifiés : `tools/agent_runner/run_daemon.py` (extension) et `tests/test_daemon_retry_cooldown.py` (nouveau). `run_ticket.py` et `run_step.py` non modifiés. La classification T018 reste la source de vérité.

## Vérifications effectuées

- Lecture complète de `tools/agent_runner/run_daemon.py`
- Lecture complète de `tests/test_daemon_retry_cooldown.py`
- Vérification des fichiers modifiés sur la branche (`git diff main...HEAD`)
- Vérification du plan approuvé (`runs/T025/plan.md`)
- Contrôle de conformité avec les critères d'acceptation du ticket

## Points validés

**Conformité ticket :**
- `quota_exceeded` → cooldown 1h, pas de stop ✓
- `provider_error` / `process_crashed` → backoff exponentiel 60s×2^n, max 5 retries puis fallback cooldown 1h ✓
- `process_failed` / `empty_output` → délai fixe 300s, max 3 retries puis `stopped=true` ✓
- `write_permission_missing` → `stopped=true` immédiat + log "human attention" ✓
- `unknown` → `stopped=true` immédiat ✓

**Architecture :**
- `run_ticket.py` non modifié ✓
- Classification T018 (runtime.log) utilisée comme source de vérité ✓
- Daemon uniquement responsable des policies ✓
- Aucun retry infini : toutes les policies sont bornées (cooldown ou stop) ✓
- `retry-state.json` daemon-owned, séparé de `state.json` — état workflow non cassé ✓

**Qualité code :**
- Écriture atomique via `.tmp` + `.replace()` (POSIX-safe) ✓
- Isolation de l'état par ticket (`runs/{id}/retry-state.json`) ✓
- Logs explicites à chaque décision de policy ✓
- Regex `\w+` correcte pour tous les failure classes connus (underscores = word chars en Python) ✓
- Lock management inchangé, check retry ajouté proprement dans `run_once` avant `launch_ticket` ✓

**Tests :**
- 35+ tests couvrant : I/O state, toutes les policies, `_is_blocked_by_retry`, `run_once`, `launch_ticket` ✓
- Tests d'intégration couvrant le cycle complet success/failure ✓

## Problèmes détectés

**Mineurs (non bloquants) :**

1. `test_apply_retry_policy_write_permission_missing_stops(tmp_path)`, `test_apply_retry_policy_unknown_stops(tmp_path)` et `test_apply_retry_policy_unrecognized_class_stops(tmp_path)` déclarent le fixture `tmp_path` sans l'utiliser. Inoffensif.

2. Aucun test explicite pour `process_crashed` atteignant `max_retries` et basculant sur le fallback cooldown. Couvert implicitement par parité avec `provider_error`.

3. `quota_exceeded` et `exponential` post-max_retries peuvent retenter toutes les heures indéfiniment. Conforme au ticket (qui ne spécifie pas de stop absolu pour ces classes).

## Risques éventuels

- `_read_last_failure_class` lit la **dernière entrée** dans l'ensemble du log, pas uniquement du run courant. Si le log accumule des entrées de runs précédents, la classe lue peut diverger. Risque mitigé : `_clear_retry_state` est appelé sur succès, réinitialisant le cycle proprement.

## Décision

- **APPROVED**

Implémentation conforme au ticket, respectueuse des contraintes d'architecture, code simple et lisible, couverture de tests solide. Les problèmes détectés sont mineurs et ne bloquent pas le merge.

## Actions demandées

Aucune action bloquante. Optionnel post-merge : nettoyer les fixtures `tmp_path` inutilisées dans les 3 tests concernés.

---

IMPLEMENTATION_APPROVED
