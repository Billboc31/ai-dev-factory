---

## Review T121 — Reconnect dashboard controls to canonical runtime daemon

### Résumé

L'implémentation est **conforme au plan approuvé** et **correcte**. 4 fichiers source modifiés (~35 lignes ajoutées), aucun fichier hors scope.

---

### Vérifications effectuées

- Diff complet `main...HEAD` sur les 4 fichiers source
- `runtime_resolver.py` — comportement des fonctions importées
- Acceptance criteria du plan vs code réel
- Intégration frontend (import wildcard `daemonApi` déjà en place)

---

### Points validés ✓

| Élément | Statut |
|---|---|
| `_pid_path()` → `resolve_runs_dir()` | ✓ |
| `_log_path()` → `resolve_logs_dir()` | ✓ |
| `_current_ticket()` → `resolve_runs_dir()` | ✓ |
| `--worktrees-dir` → `resolve_worktrees_dir()` | ✓ |
| `log.parent.mkdir(parents=True, exist_ok=True)` avant log open | ✓ |
| `sync_main()` — subprocess sans shell, timeout 60s, gestion OSError/Timeout | ✓ |
| `POST /daemon/sync-main` endpoint | ✓ |
| Bouton "Sync Main" dans `DaemonPage.jsx` avec feedback inline | ✓ |
| Dual-mode : avec/sans `AI_DEV_FACTORY_RUNTIME_ROOT` | ✓ |
| Aucune régression sur Start/Stop/Restart/Board | ✓ |

---

### Observations (non bloquantes)

1. **Aucun test ajouté** — `sync_main()` n'est pas testé (subprocess mocké manquant). Acceptable pour ce scope.

2. **`resolve_ticket_cwd()` toujours hardcodé** — `runtime_resolver.py:92` utilise encore `project_root / "runs"` directement. Hors scope T121, mérite un ticket futur.

3. **Scope gap ticket ↔ plan** — retry/approve/abort/archive et logs live sont exclus du plan. L'implémentation est correcte par rapport au plan approuvé ; ces fonctionnalités restent à traiter séparément.

---

### Décision

L'implémentation est fidèle au plan, le code est propre et sans régression identifiable.

IMPLEMENTATION_APPROVED
