---

# PR Review — T140 — Isolated sandbox runtimes and supervisors

## Résumé

Implémentation correcte et complète. 4 fichiers modifiés, 0 régression. Tous les critères d'acceptation du ticket sont satisfaits.

## Vérifications effectuées

Lecture du diff complet vs `main` (4 fichiers), du plan, et des 4 nouveaux tests.

## Points validés

**Isolation runtime root** — `sandbox_runtime_root = {sandboxes_dir}/{sandbox_id}/runtime` calculé identiquement dans SandboxManager et run_sandbox.py. Les sous-dossiers `state/`, `logs/`, `runs/` sont pré-créés avant le démarrage du supervisor.

**Isolation supervisor port** — formule `8090 + slot` cohérente entre les deux couches. Slot 0 = port 8090 réservé au supervisor principal, sandboxes sur slot ≥ 1. Confirmé par les assertions de test.

**Injection d'environnement** — l'ancien `os.environ.get("AI_DEV_FACTORY_SUPERVISOR_PORT", "8090")` est supprimé et remplacé par le port calculé. `AI_DEV_FACTORY_SUPERVISOR_URL` est aussi injecté (nouveau). `extra_env` dans `_do_sandbox()` mis à jour avec les deux nouvelles variables.

**Cycle de vie supervisor** — spawn uvicorn isolé avec `AI_DEV_FACTORY_RUNTIME_ROOT` overridé, écriture `supervisor.pid`, SIGTERM→wait(5s)→SIGKILL→dégradation gracieuse, bloc `finally` garantissant l'arrêt.

**Cleanup sûr** — `_terminate_sandbox_supervisor()` lit le PID file et envoie SIGTERM uniquement au processus sandbox. Seul `{sandboxes_dir}/{sandbox_id}` est supprimé. Runtime principal non touché.

**Concurrence** — double protection (threading.Lock dans SandboxManager, fcntl.LOCK_EX dans run_sandbox.py). Test avec 5 threads concurrents : 5 ports distincts, 5 roots distincts, 0 collision.

**Tests** — 4 nouveaux tests couvrant isolation root, isolation port, concurrence, et safety cleanup. Tous passent.

## Problèmes détectés

**Observation 1 — Dérive du plan : pas de supervisor passthrough** (non bloquant)  
Le plan prévoyait de passer `supervisor_port` et `sandbox_runtime_root` via `sandbox_runner.py` → `supervisor/main.py`. L'implémentation calcule ces valeurs indépendamment avec la même formule. Acceptable : les formules sont identiques, le registre de slots est partagé, la coordination cleanup passe par le `supervisor.pid` sur filesystem.

**Observation 2 — Pas de tests unitaires pour les fonctions worker** (non bloquant)  
`_start_sandbox_supervisor()`, `_stop_sandbox_supervisor()`, `_write_sandbox_env()` dans run_sandbox.py ne sont pas testés unitairement. Les tests couvrent uniquement SandboxManager.

**Observation 3 — Pas de health check après spawn supervisor** (non bloquant)  
Le supervisor est considéré prêt dès que le `Popen` réussit, sans attendre qu'il accepte des connexions. Risque transitoire mineur sur les premières requêtes containers.

**Observation 4 — Failure silencieuse si supervisor ne démarre pas** (non bloquant)  
Si `_start_sandbox_supervisor()` lève une `OSError`, le pipeline continue sans supervisor. Le log enregistre l'erreur.

## Décision

Implémentation complète, correcte et sûre. Les observations sont mineures et sans impact sur le comportement attendu en usage normal.

IMPLEMENTATION_APPROVED
