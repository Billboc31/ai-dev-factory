Plan écrit dans `runs/T019/plan.md` et snapshot ticket dans `runs/T019/ticket.md`.

Résumé du plan :

**Fichiers touchés** : `run_ticket.py` (seul fichier modifié) + `tests/test_ticket_source.py` (nouveau).

**4 étapes** :
1. Ajouter `_copy_ticket_source()` — validation (traversal, fichier absent, répertoire), copie, log
2. Ajouter `--ticket-source` au parser CLI (optionnel, lié à `--auto-init`)
3. Intégrer dans `init_auto()` — après création de `state.json`, copier si fourni
4. 6 tests ciblés : copie valide, fichier absent, traversal, répertoire, intégration avec init, init sans option inchangé

**Risques identifiés** : traversal path (bloqué sur le chemin brut avant résolution), collision ticket.md (acceptable car bloquée en amont par state.json), snapshot stale (comportement voulu).
