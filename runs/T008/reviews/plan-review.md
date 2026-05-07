J'ai maintenant lu les deux fichiers principaux. Voici ma review structurée.

---

## Review — T008 mode `--auto` (Implementation)

**Date :** 2026-05-08  
**Verdict :** `IMPLEMENTATION_FIX_REQUIRED`

---

### 1. État de l'implémentation

**L'implémentation est absente.**

`run_ticket.py` ne contient ni `--auto`, ni `--auto-init`, ni aucun des composants planifiés :

| Élément planifié | Présent ? |
|---|---|
| Flag `--auto` dans `parse_args()` | Non |
| Flag `--auto-init` dans `parse_args()` | Non |
| `init_auto()` / `load_state()` / `save_state()` | Non |
| `auto_run()` avec gates pré-exécution | Non |
| `determine_next_state()` avec détection de mots-clés | Non |
| `append_workflow_journal()` | Non |
| `runs/T008/state.json` | Non |
| Section `--auto` dans README.md | Non |

Le fichier `run_ticket.py` est identique à son état pré-T008 : il expose `--once`, `--branch`, `--commit`, `--push` uniquement.

---

### 2. Cohérence du plan (v2) — à titre informatif

Le plan v2 est structurellement solide. Les points suivants méritent attention lors de l'implémentation :

**Tension entre `run_step.py` et `state.json` :**  
`run_step.py` utilise encore `read_next_step()` qui lit `workflow-status.md` pour déterminer l'étape suivante. Le plan v2 dit que `run_step.py` n'est pas modifié, et que `workflow-status.md` ne sert que de journal. C'est cohérent — `--auto` appelle `run_step.py` en passant l'étape explicitement, sans lui laisser la décision. Pas de conflit, mais le coder devra s'assurer que `call_run_step()` passe toujours le step résolu par `auto_run()`.

**Détection de mots-clés :**  
Le plan spécifie `^KEYWORD$` en multilignes. `run_step.py` écrit la sortie stdout dans un fichier via `write_output()`, mais `auto_run()` devra capturer cette même stdout pour analyser les mots-clés. Si `run_step.py` intercepte stdout, `auto_run()` doit recapturer la sortie brute — s'assurer que `call_run_step()` capture stdout directement (pas via `print_result()`).

**Écriture atomique de `state.json` :**  
Le plan mentionne write + rename. Sur macOS, `Path.rename()` est atomique sur le même filesystem. À implémenter correctement.

---

### 3. Problèmes bloquants

1. **Aucun code à reviewer.** L'implémentation complète est à produire.
2. **README.md** est vide (2 lignes) — section `--auto` absente.

---

### 4. Points non-bloquants (à vérifier lors de la prochaine review)

- Gate 5 (working tree propre) : `git status --porcelain` doit être strict — vérifier que les fichiers untracked sont aussi bloquants.
- Keyword multi-match : le plan dit "premier trouvé utilisé" — s'assurer que l'ordre de recherche est déterministe (ordre de définition dans la table des transitions).
- `state.json` non versionné : à confirmer via `.gitignore` ou documentation explicite.

---

### Conclusion

`IMPLEMENTATION_FIX_REQUIRED` — l'implémentation n'existe pas. Le plan v2 est valide et peut être codé directement.
