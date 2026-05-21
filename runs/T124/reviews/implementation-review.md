---

## Review — T124 implementation

**Verdict: IMPLEMENTATION_APPROVED**

### Contexte de périmètre

La plan review avait explicitement scoppé T124 à un **V1 read-only** : découverte de projets + sélection UI uniquement. Les opérations runtime project-scoped sont reportées à un ticket de suivi. L'implémentation suit fidèlement ce V1.

---

### Points validés

**Backend**
- `ProjectRegistry` : scan propre des sous-dossiers git, gestion correcte des `.git`-fichiers (worktrees), fallback silencieux sur `list_tickets`
- `from_single_root()` assure la rétrocompatibilité sans toucher aux routes existantes
- `main.py` : env var `AI_DEV_FACTORY_PROJECTS_ROOT` + arg CLI `--projects-root`, wiring non-intrusif
- Routes existantes (`/daemon`, `/tickets`, `/project-map`, `/health`) inchangées — conforme à la plan review

**Frontend**
- `useProjects` : polling 10s cohérent avec le reste de la codebase
- `ProjectSidebar` : rendu minimal et correct, highlight actif, callback `onSelect`
- `App.jsx` : state `activeProject` initialisé sur le premier projet retourné, affiché dans le header

**Tests** : 19 cas au total (10 unit + 9 intégration). Le cas `test_git_file_entry_not_treated_as_repo` est particulièrement soigné.

---

### Observations mineures (non-bloquantes)

1. **`eslint-disable` dans App.jsx ligne 40** — `activeProject` absent des dépendances `useEffect`. Le comportement est correct mais le lint-suppress est un code smell ; ajouter `activeProject` aux deps serait idiomatiquement propre.
2. **Pas d'état loading/error dans la sidebar** — UX dégradée si l'API est indisponible au démarrage. Acceptable pour V1.
3. **Registre scanné une seule fois** — un nouveau projet ajouté à chaud nécessite un redémarrage. Comportement attendu pour V1.

---

### Pour le ticket de suivi

- Brancher `activeProject` sur les pages (`TicketsPage`, `BoardPage`, `DaemonPage`)
- Ajouter des routes backend project-scoped utilisant `ProjectRegistry.resolve()`
- Corriger l'`eslint-disable` dans App.jsx

La review est enregistrée dans `runs/T124/reviews/implementation-review.md`.

IMPLEMENTATION_APPROVED
