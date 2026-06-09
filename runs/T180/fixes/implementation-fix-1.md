# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T180/reviews/implementation-review.md
- generated at: 2026-06-09T12:10:10Z

---

IMPLEMENTATION_FIX_REQUIRED

---

## Résumé de la review

L'implémentation backend est solide : parsing `healthcheck.sh` stdout → `healthcheck_diagnostics`, nouvel endpoint `/diagnostics`, wiring complet dans `run_sandbox.py` et `sandbox_runtime_deploy.py`, tests mis à jour sans régression.

**Problème bloquant** : `backend_diagnostics` est fetché par l'API mais silencieusement ignoré dans le frontend. Or c'est précisément là que vivent les informations prioritaires du ticket :

| Champ ticket | Source | Rendu UI actuel |
|---|---|---|
| Traefik route diagnostics | `backend_diagnostics.traefik_probe` | ❌ absent |
| backend container status | `backend_diagnostics.api_container` | ❌ absent |
| resolved backend URL | `backend_diagnostics.backend_urls` | ❌ absent |
| network diagnostics | `backend_diagnostics.traefik_networks` | ❌ absent |
| validation.json `failure_type` | `backend_diagnostics.failure_type` | ❌ absent |

Le plan approuvé mentionnait explicitement "probe table + **backend_diagnostics fields**". Les critères "Traefik/proxy routing issues visible without raw logs" et "validation.json diagnostics surfaced" ne sont pas satisfaits.

**Problème mineur** : aucun test unitaire pour `_parse_healthcheck_output` malgré la logique regex critique.

**Corrections requises** :
1. Dans `LogViewerDrawer`, utiliser `res.data.backend_diagnostics` et le rendre dans la section "Failure details" (failure_type, backend_urls, statut container API, sondes Traefik).
2. Ajouter des tests unitaires minimaux pour `_parse_healthcheck_output`.
