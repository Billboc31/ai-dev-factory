I have a complete picture. Writing the review now.

---

## Review — T154 — Stabilize Traefik dynamic route lifecycle

### Résumé

This is the review following the `IMPLEMENTATION_FIX_REQUIRED` decision on `implementation-fix-1.md`, which flagged three blockers: hardcoded URL in `_wait_for_proxy_url()`, wrong probe endpoint in `healthcheck.sh`, and undistinguished log messages. All three corrections are now present in the current code. Changeset remains minimal (4 files, ~75 lines), scoped correctly to the two remaining gaps identified in the plan.

---

### Vérifications effectuées

- Read `_wait_for_proxy_url()` signature and body in `run_sandbox.py:281–301`
- Read `_register_proxy_route()` return type and call site (`run_sandbox.py:254–278`, `1006–1009`)
- Read `healthcheck.sh` full file
- Read `test_proxy_route_wait.py` (4 tests)
- Read `test_healthcheck_classification.py` (1 integration test)
- Verified `test_proxy_manager.py` route directory isolation
- Read `proxy_manager.py` full file
- Cross-checked all three blockers from `implementation-fix-1.md` against current code

---

### Points validés

**Bloquant 1 résolu** — `_wait_for_proxy_url(url: str, log_path, ...)` prend l'URL en paramètre direct (`run_sandbox.py:281`). `_register_proxy_route()` retourne `urls.get("api")` (ligne 275). Call site : `api_url = _register_proxy_route(...); if api_url: _wait_for_proxy_url(api_url, log_path)` (lignes 1007–1009). Pas de reconstruction manuelle du domaine. ✓

**Bloquant 2 résolu** — `healthcheck.sh:74` : `probe "proxy-infra" "${SANDBOX_API_URL}" || echo "PROXY_INFRA_FAIL"`. Pas de référence à `http://traefik.ai-dev-factory.localhost`. ✓

**Bloquant 3 résolu** — HTTP 200 → `"proxy: route active (backend healthy)"` (ligne 292). `HTTPError` → `"proxy: route active (backend not healthy yet)"` (ligne 296). Les deux cas sont distingués dans les logs et couverts par les tests `test_wait_returns_true_when_backend_healthy` et `test_wait_returns_true_when_traefik_responds_http_error`. ✓

**Atomic write** — `proxy_manager.py:126–128` : `tmp_file.write_text(content)` suivi de `tmp_file.rename(route_file)`. Traefik ne voit jamais de fichier `.yml.tmp`. Inchangé et correct. ✓

**Idempotent unregister** — `proxy_manager.py:147–151` : `route_file.unlink()` + catch silencieux `FileNotFoundError`. Ne touche que `{sandbox_id}.yml`. ✓

**Stale cleanup** — `proxy_manager.py:153–186` : préserve tous les fichiers `_`-préfixés ; expose `list[str]` pour assertion. Câblé via `SandboxManager.cleanup_stale_routes()`. Couvert par 5 tests dans `test_proxy_manager.py` et 1 dans `test_sandbox_manager.py`. ✓

**Protection Traefik global** — `unregister()` et `cleanup_stale_routes()` ne peuvent pas supprimer `_dashboard.yml` ni aucun fichier `_`-préfixé (logique `_INFRA_PREFIX`). Le bloc `finally` de `_do_sandbox` appelle uniquement `_unregister_proxy_route()` (ligne 1127). ✓

**Isolation des tests** — `test_proxy_manager.py` (fixture `mgr` → `tmp_path/routes`), `test_proxy_route_wait.py` (log via `tmp_path`), `test_healthcheck_classification.py` (`cwd=tmp_path`, PATH injection). Aucune référence au répertoire réel `~/runtime/ai-dev-factory/proxy/routes`. ✓

**Scope borné** — Aucun changement à `sandbox_manager.py`, au deploy loop, à l'infra Traefik, ni aux tests pré-existants. ✓

---

### Problèmes détectés

#### Observation 1 — `time.sleep` non mocké dans les tests de timeout (minor)

`test_wait_returns_false_on_connection_error` et `test_wait_logs_infra_failure` utilisent `timeout_s=2` sans mocker `time.sleep`. Ces deux tests dorment 2 secondes réelles à chaque exécution. Acceptable, mais ralentit la suite inutilement.

Correction suggérée (non bloquante) :
```python
with patch("run_sandbox.time.sleep"):
    result = run_sandbox._wait_for_proxy_url(_TEST_URL, log, timeout_s=2)
```

#### Observation 2 — probe proxy-infra sur-sensible avec `curl -sf` (cosmétique)

`probe "proxy-infra" "${SANDBOX_API_URL}"` utilise `curl -sf`. Le flag `-f` fait échouer curl sur toute réponse 4xx/5xx. Si le backend applicatif répond 404 sur sa racine, `PROXY_INFRA_FAIL` est émis alors que Traefik route correctement. Le plan-fix-1 avait mentionné cette alternative (sonder avec en-tête Host sur 127.0.0.1) mais l'avait classée comme suggestion, pas comme requis. Le comportement actuel est conservateur (over-reporting infra failures) mais acceptable pour le périmètre "stabilize".

#### Observation 3 — Test d'écriture atomique implicite seulement (cosmétique)

`test_register_creates_route_file` vérifie l'existence finale du fichier `.yml`, mais ne vérifie pas l'absence de résidu `.yml.tmp`. Non bloquant pour le ticket.

---

### Risques éventuels

Aucun risque bloquant. `_wait_for_proxy_url()` retournant `False` n'arrête pas le sandbox — c'est intentionnel (résilience, healthcheck.sh reste l'arbitre). Le timeout fixe à 15s est non configurable mais adapté au scope.

---

### Décision

Les trois blockers identifiés dans `implementation-fix-1.md` sont tous corrigés. Les critères d'acceptation du plan sont remplis. Le changeset est propre, scoped, sans drift. Les observations restantes sont mineures et non bloquantes.

IMPLEMENTATION_APPROVED
