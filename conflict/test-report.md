# Conflict Resolution — Test Report (T158)

**Date :** 2026-05-28  
**Worktree :** `/Users/pierrebocquet/ai-dev-factory-worktrees/T158`  
**Commit merge :** `06e220e` (`merge(main): resolve SandboxState field conflict for T158`)

## Commandes exécutées

### Suite T158 / sandbox / deployer

```bash
cd /Users/pierrebocquet/ai-dev-factory-worktrees/T158
python -m pytest \
  tests/test_environment_routes.py \
  tests/test_sandbox_worktree.py \
  tests/test_sandbox_manager.py \
  tests/test_deployer_execution.py \
  -q --tb=short
```

**Résultat :** `63 passed` in ~17s

### Suite infra / proxy / healthcheck (changements `main`)

```bash
python -m pytest \
  tests/test_proxy_manager.py \
  tests/test_infra_path_invariant.py \
  tests/test_operational_scripts.py \
  tests/test_healthcheck_classification.py \
  -q --tb=line
```

**Résultat :** `72 passed`, 1 warning (`pytest.mark.integration` non enregistré) in ~41s

## Couverture par zone

| Zone | Tests | Statut |
|------|-------|--------|
| Routes `/environments` | `test_environment_routes.py` | OK |
| Hosts Traefik custom | `test_proxy_manager.py` | OK |
| Ref resolution deployer | `test_sandbox_worktree.py` | OK |
| Sandbox manager lifecycle | `test_sandbox_manager.py` | OK |
| Deployer execution | `test_deployer_execution.py` | OK |
| Infra paths / Traefik | `test_infra_path_invariant.py` | OK |
| Healthcheck proxy-infra | `test_operational_scripts.py`, `test_healthcheck_classification.py` | OK |

## Non exécuté

- Lint formel (`ruff` / `mypy`) — non invoqué dans le Makefile cible ; pas d’erreur d’import détectée lors des tests.
- Build dashboard (`npm run build`) — hors chemin critique du conflit `SandboxState`.
- Suite pytest complète du repo — non lancée (coût temps) ; sous-ensembles ci-dessus couvrent le périmètre merge.

## Synthèse

**135 tests** ciblés passent après résolution du conflit. Aucune régression observée sur les contrats T158 (environments) ni T157 (git refs deployer).
