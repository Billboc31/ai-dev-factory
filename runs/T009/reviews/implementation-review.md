J'ai lu les trois fichiers. Voici la review.

---

## Review T009 — Artifact-aware fix loop

### `run_step.py` — `--extra-context-file`

**Séparateur** (L228–232) : conforme au plan, texte exact `\n\n---\n\n## Contexte de retry injecté par run_ticket.py\n\n`.

**Sécurité** : `ensure_safe_relative_path` appelé sur le chemin (L224) — protection path traversal, cohérent avec le reste du fichier.

**Garde d'existence** (L225–226) : lève `RunnerError` avec le chemin exact si fichier absent — exit code 2.

**Condition** : la branche `if args.extra_context_file` n'altère rien si le flag est absent. Comportement neutre confirmé.

---

### `run_ticket.py` — 3 fonctions + `auto_run`

**`_collect_fix_artifacts`** (L260–298)

- `previous_output` : chemin fixe via `DEFAULT_OUTPUTS["planner"]` / `DEFAULT_OUTPUTS["coder"]` — exactement les mêmes clés que `run_step.py`. Pas de magic string isolée.
- `review` : glob par état (`plan-review*.md` / `implementation-review*.md`), sélection par `[-1]` sur tri mtime. Couvre stable et versionné.
- `fix_instructions` : filtre `context-*` appliqué ligne 287–289. Défensif et correctement documenté (le pattern `plan-fix-*.md` les exclut déjà structurellement).
- Messages d'erreur : trois cas distincts, chemin exact ou glob exact dans chaque message. Claire et actionnable.

**`_build_fix_context_file`** (L301–317)

- Chemin : `runs/TXXX/fixes/context-<ts>.md` — conforme au plan.
- Sections : `## Output précédent`, `## Review`, `## Instructions de fix` — labels explicites.
- Séparateur : `\n\n---\n\n` entre sections.

**`_call_run_step`** (L230–257)

- Signature étendue `extra_context_file: Path | None = None` — rétrocompatible.
- Chemin passé comme `str(extra_context_file)` (L241) — chemin relatif, valide pour `ensure_safe_relative_path` dans `run_step.py`.

**`auto_run`** (L373–447)

- Gate fix-state (L412–423) : `_collect_fix_artifacts` en premier, puis `_build_fix_context_file` — ordre correct, évite que le fichier context nouvellement créé ne se retrouve dans la collection.
- Logging (L421–423) : chaque artefact loggé par clé+chemin, puis `context_file`. Format exact du plan.
- Erreur de collection : catchée, loggée dans `runtime.log`, retour code 2. L'état n'est pas modifié.
- Aucune boucle : `auto_run` s'arrête après une transition. La relance est manuelle.

**`state.json` source de vérité** : toutes les décisions passent par `load_state` / `save_state`. `workflow-status.md` n'est écrit qu'en journal après la transition (L444), jamais lu pour décider.

---

### `README.md`

- Conventions de nommage : reviews stable/versionné, fix files par état.
- Règle de sélection mtime documentée.
- `context-*.md` : explication de l'exclusion et de l'origine générée.
- Workflow en 3 étapes, commande de relance exacte.
- Exemple `runtime.log` complet et cohérent avec le code.

---

### Observations mineures (non bloquantes)

1. **Filtre `context-*` jamais activé** : le glob `fixes/plan-fix-*.md` ne peut pas matcher `context-*.md`. Le filtre est défensif — c'est intentionnel et documenté. Acceptable.

2. **`_build_fix_context_file` hors try-except** dans `auto_run` : une `IOError` (disque plein, permissions) produirait un traceback Python non nettoyé. Cas extrême, non requis par le plan, mais notable.

---

### Verdict

**IMPLEMENTATION_APPROVED**

Les cinq invariants du plan sont respectés : contexte reconstruit correctement, artefacts loggés explicitement, erreurs claires avec chemin exact, aucune boucle automatique, `state.json` seule source de vérité. Le README couvre toutes les conventions requises.
