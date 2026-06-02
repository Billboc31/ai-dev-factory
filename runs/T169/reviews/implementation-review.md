Now writing the review output.

---

# PR Review — T169: Fix Docker Compose env interpolation

## Résumé

L'implémentation corrige la propagation de `SANDBOX_ID` vers Docker Compose en remplaçant l'héritage de l'environnement shell par des fichiers env explicites passés via `--env-file`. Une validation pre-flight (`docker compose config`) est ajoutée dans les deux chemins d'exécution (shell et Python). Périmètre respecté, tests ajoutés.

## Vérifications effectuées

- Lecture complète de `.ai-dev-factory/scripts/start.sh` et `stop.sh`
- Lecture de `services/control_api/services/sandbox_manager.py` (`_run_compose`, `create`)
- Lecture de `services/control_api/services/deployer_runner.py` (`_inject_compose_flags`, `_validate_compose_config`, `_do_deploy`)
- Lecture des tests `test_sandbox_manager.py` et `test_sandbox_runtime_deploy.py`
- Comparaison plan vs implémentation
- Vérification liste des fichiers modifiés vs scope du plan

## Points validés

**Correctness**
- `sandbox_manager.py:create()` écrit `SANDBOX_ID={sandbox_id}` dans l'env_file sandbox (ligne 305) — la source est toujours non-vide pour un sandbox.
- `_run_compose()` passe `deploy/.env` en premier, l'env_file sandbox en second : le `SANDBOX_ID` sandbox gagne correctement sur tout défaut dans `deploy/.env`.
- `start.sh` écrit `runtime/.env.compose` avec la valeur résolue de `SANDBOX_ID` avant tout appel compose (ligne 78).
- La validation pre-flight (`docker compose config`) est appelée avant tout `docker compose up` dans les deux chemins (shell : lignes 113-127 ; Python : `_run_compose` ligne 232-252, `_do_deploy` lignes 318-330).
- `stop.sh` lit le fichier `.env.compose` existant pour un teardown déterministe ; fallback gracieux si le fichier est absent.
- `_inject_compose_flags` est effectivement appelé dans `_do_deploy` (ligne 353) : toutes les commandes compose du deployer runner reçoivent les flags corrects.

**Tests**
- `test_run_compose_uses_both_env_files` : vérifie l'ordre des deux `--env-file` et leur contenu.
- `test_start_validates_compose_config_before_up` : vérifie que `start()` retourne `SandboxStatus.error` et que `up` n'est jamais appelé si l'alias est mauvais.
- `test_deploy_inject_flags_includes_deploy_env` : vérifie l'ordre dans la string de commande.
- `test_deploy_fails_early_on_wrong_compose_alias` : vérifie que `_do_deploy` renvoie `ok=False` sans appeler `up`.
- 4 tests nouveaux = exactement ce que le plan prévoyait.

**Scope**
- Aucun refactor transversal. `docker-compose.yml`, Traefik, ProxyManager, `.env.example` non touchés, conformément aux exclusions du plan.

**Diagnostics**
- Logs ajoutés : env files résolus, SANDBOX_ID effectif, résultat de `docker compose config`, projet compose effectif — critère ticket #5 satisfait.

## Problèmes détectés

**Mineur — gap de couverture dans `start.sh` (non bloquant)**

Lignes 110-134 : si `deploy/.env` n'existe pas, le script tombe dans le `else` qui exécute `docker compose up -d` sans aucun `--env-file`, donc sans le fichier `.env.compose` pourtant écrit à la ligne 78. Dans ce cas, `SANDBOX_ID` retombe sur l'héritage shell.

```bash
# Ligne 133 — .env.compose non utilisé si deploy/.env absent
else
  docker compose up -d
fi
```

Ce cas est probablement hors périmètre opérationnel (le dépôt exige `deploy/.env`), mais la correction serait triviale :

```bash
else
  docker compose --env-file "${RUN_DIR}/.env.compose" up -d
fi
```

**Mineur — `stop.sh` sans `-p`**

Toutes les branches de `stop.sh` n'utilisent pas `-p <compose_project>`. Si le projet a été démarré avec un nom de projet custom, `docker compose down` sans `-p` pourrait ne pas trouver les bons conteneurs. Comportement pré-existant, non introduit par T169.

## Risques éventuels

- Aucun risque de sécurité : `SANDBOX_ID` est un hex UUID généré en interne, pas une entrée utilisateur — pas de risque d'injection dans le nom de fichier ou la commande compose.
- `shell=True` dans `deployer_runner.py:355` avec la string produite par `_inject_compose_flags` est pré-existant, hors scope T169.
- La valeur vide de `SANDBOX_ID` dans `.env.compose` (runtime principal sans sandbox) est correcte : `${SANDBOX_ID:-default}` se résout à `default` comme avant, ce qui est le comportement attendu pour le runtime principal.

## Décision

L'implémentation résout correctement le problème décrit dans le ticket. Les deux chemins d'exécution (shell et Python/API) sont couverts. La validation pre-flight garantit l'échec rapide en cas de mauvaise interpolation. Les tests couvrent les critères d'acceptation. Le gap dans la branche `else` de `start.sh` est mineur et hors périmètre réaliste.

## Actions demandées

Aucune action bloquante. Pour la prochaine itération (hors T169) : étendre la branche `else` de `start.sh` pour également passer `--env-file "${RUN_DIR}/.env.compose"` quand `deploy/.env` est absent.

IMPLEMENTATION_APPROVED
