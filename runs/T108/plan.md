Le plan est écrit à `runs/T108/plan.md`. Voici le résumé :

---

## Plan T108 — Multi-project onboarding and project registry

### Architecture cible

Le plan introduit 5 composants nouveaux autour d'un registre SQLite global (`~/.ai-dev-factory/registry.db`) :

**1. SQLite registry** — `services/control_api/db/registry.py`
Deux tables : `projects` (id, name, project_root, remote_url, status) et `project_health` (daemon_running, active_workers, last_incident). Initialisé au démarrage de l'API.

**2. Schéma `project.yml`** — `ai/templates/project-template.yml`
Fichier de config par dépôt géré : stack, commandes build/test/run, ports, guardian config.

**3. Deux nouveaux CLIs**
- `create_project.py` — crée un nouveau repo avec git init + project.yml + enregistrement SQLite
- `bootstrap_project.py` — analyse un repo existant (détection heuristique de stack), génère project.yml, enregistre en mode `observe`

**4. Router API `/projects`** — `services/control_api/routes/projects.py`
`GET/POST/DELETE /projects`, `GET /projects/{id}/board`, `GET /projects/{id}/health`. Le board par projet délègue à `board_service.get_board()` avec le `project_root` résolu depuis le registry.

**5. Dashboard Projects page** — `apps/dashboard/src/pages/ProjectsPage.jsx`
Liste des projets avec santé (daemon, workers, incidents). Lien vers le board isolé de chaque projet.

### Hors scope
Guardian framework, daemon global cross-projets, UI de création projet (CLI seulement), isolation mémoire projet, issue tree cross-projets.

### Risques principaux
Concurrence SQLite (mitigé par WAL mode), stack non détectée au bootstrap (valeurs vides valides), régressions sur routes existantes (aucun changement aux routes `/tickets`, `/daemon`, `/board`).
