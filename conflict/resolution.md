# Conflict Resolution — T158

**Branche :** `ticket/T158-t158-add-named-environments-with-configurable-trae`  
**PR :** [#168](https://github.com/Billboc31/ai-dev-factory/pull/168)  
**Worktree :** `/Users/pierrebocquet/ai-dev-factory-worktrees/T158`  
**Merge :** `origin/main` → branche T158 (commit `06e220e`)

## Contexte

T158 ajoute le workflow **Environments** (environnements nommés persistants, hosts Traefik configurables, metadata lifecycle).  
`main` avait avancé avec **T157** (fetch/checkout de branche côté deployer) et les merges **T154–T156** (infra Traefik, healthcheck, runtime tab).

Le conflit Git n’apparaissait qu’à l’union des deux lignées sur le modèle `SandboxState`.

## Fichiers en conflit

| Fichier | Statut |
|---------|--------|
| `services/control_api/models/sandbox.py` | Conflit résolu (union des champs) |

## Fichiers fusionnés automatiquement (sans marqueurs)

| Fichier | Notes |
|---------|--------|
| `services/control_api/services/sandbox_manager.py` | Logique T157 `create_with_worktree` + API T158 `create()` conservées |
| `services/control_api/routes/deployer.py` | Propagation branche deployer depuis `main` |
| `tests/test_sandbox_worktree.py` | Tests ref resolution T157 |

## Détail du conflit : `sandbox.py`

### HEAD (T158)

Champs pour environnements nommés :

- `env_name`, `env_type`
- `ref`, `ref_type` — intention utilisateur (branche/tag/commit choisi à la création)
- `deployment_mode`
- `web_host`, `api_host` — URLs Traefik personnalisées
- `deployed_at`, `stopped_at` — lifecycle

### `origin/main` (T157)

Champs pour résolution Git après deploy :

- `requested_ref` — ref demandée au deployer
- `resolved_ref` — ref distante résolue (`origin/...`)
- `commit_sha` — SHA du worktree détaché

### Résolution choisie

**Conserver les deux jeux de champs** sur `SandboxState`.

**Pourquoi :**

- Sémantiques distinctes : `ref` = config produit environnement ; `requested_ref`/`resolved_ref`/`commit_sha` = trace technique post-fetch.
- `sandbox_manager.py` utilise déjà les deux : `create(..., ref=...)` pour environments et `create_with_worktree(..., requested_ref=...)` pour deployer.
- Supprimer un côté casserait soit le dashboard Environments (T158), soit les tests/assertions deployer (T157).
- Pas de duplication fonctionnelle : les noms et usages ne se chevauchent pas.

### Extrait final

```python
    env_name: str | None = None
    env_type: EnvironmentType | None = None
    ref: str | None = None
    ref_type: RefType | None = None
    deployment_mode: EnvironmentMode | None = None
    web_host: str | None = None
    api_host: str | None = None
    deployed_at: str | None = None
    stopped_at: str | None = None
    requested_ref: str | None = None
    resolved_ref: str | None = None
    commit_sha: str | None = None
```

## Décisions importantes

1. **Union plutôt que choix binaire** — aligné avec la vision T158 + contrats runtime récents de `main`.
2. **Pas de reset / pas de `--ours`/`--theirs` global** — merge explicite fichier par fichier.
3. **Artefacts `runs/T157/*`** — intégrés via merge `main` (historique workflow), hors scope fonctionnel T158.
4. **Aucun marqueur Git restant** — vérifié sous `services/`.

## Risques résiduels

- **Évolution future** : si un flux unifie `ref` et `requested_ref`, documenter la migration pour éviter deux sources de vérité côté UI.
- **États JSON anciens** : les champs optionnels Pydantic restent compatibles ; pas de migration DB requise (fichiers JSON sandbox).
- **`__pycache__` modifié localement** — non commité ; à ignorer ou ajouter au `.gitignore si gênant.

## Prochaine étape opérationnelle

```bash
cd /Users/pierrebocquet/ai-dev-factory-worktrees/T158
git push origin ticket/T158-t158-add-named-environments-with-configurable-trae
```
