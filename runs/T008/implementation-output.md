Tous les tests passent. Voici un résumé de ce qui a été implémenté :

---

## Implémentation T008 — mode `--auto`

### `run_ticket.py` — nouveaux composants

**Constants :**
- `VALID_STATES` — frozenset des 8 états valides
- `TRANSITIONS` — table explicite état → (step, is_deterministic, possible_next_states)
- `DEFAULT_OUTPUTS` — mapping step → fichier de sortie (en sync avec `run_step.py`)

**Helpers privés :**
- `load_state()` / `save_state()` — lecture/écriture atomique de `state.json` (write + rename), avec validation stricte
- `_log_runtime()` — append dans `runs/TXXX/runtime.log`
- `_get_current_branch()` / `_check_working_tree_clean()` — gates git
- `_determine_next_state()` — détection de mots-clés par regex `^KEYWORD$` multilignes ; first-found si plusieurs
- `_call_run_step()` — invoque `run_step.py --exec-cmd`, lit le fichier de sortie pour l'analyse keyword
- `_append_workflow_journal()` — append-only dans `workflow-status.md`, jamais lu

**Commandes :**
- `init_auto()` → `--auto-init --branch-slug <slug>` : crée `state.json` avec `INIT`, vérifie branche, refuse si déjà existant
- `auto_run()` → `--auto --exec-cmd <cmd>` : 5 gates pré-exécution (state valide, non-terminal, branche, working tree propre, exec-cmd fourni), transition d'état, journal

**Exit codes :**
- `2` sur tout gate bloquant
- `0` sur `TEST_COMPLETE` avec message "workflow complete — no automatic merge"
- `1` si aucun keyword review trouvé (état inchangé, warning visible)

### `README.md` — section `--auto` complète
- Prérequis, `--auto-init`, `--auto`, table des gates, diagramme des états, exemple session complète, invariants.
