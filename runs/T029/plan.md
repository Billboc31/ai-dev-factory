Le plan est écrit. Voici le résumé :

---

## Plan T029 — Dashboard UI minimal

**Stack** : React + Vite + TypeScript + React Router v6 + Vitest + @testing-library/react.

**Structure** : `apps/dashboard/` en module standalone, sans toucher à `services/control_api/` ni aux tests Python existants.

### 8 étapes d'implémentation

1. **Scaffolding** — `package.json`, `vite.config.ts` (proxy `/api` → `:8080`), `index.html`, `setupTests.ts`
2. **`src/api.ts`** — Types TypeScript miroir des schémas Pydantic + wrapper `apiFetch` (gère JSON vs `text/plain`) + toutes les fonctions pour chaque endpoint
3. **Composants partagés** — `ErrorBanner` (erreur API) + `ActionButton` (loading/succès/erreur)
4. **`TicketsPage` (`/`)** — tableau tickets avec état coloré + liens + bouton refresh
5. **`TicketDetailPage` (`/tickets/:id`)** — résumé, tabs lazy (logs/plan/review/tests/artefacts), boutons workflow conditionnels selon état, boutons Git
6. **`DaemonPage` (`/daemon`)** — statut avec polling 5s, boutons Start/Stop/Restart
7. **`App.tsx`** — routing BrowserRouter + navbar
8. **Tests** — mocks Vitest pour api.ts, TicketsPage, TicketDetailPage, DaemonPage

### Points clés de conception

- `run-next` retourne 202 (async) → l'UI affiche "Dispatched in background", pas de fausse promesse de résultat synchrone
- Endpoints logs/plan/review/tests retournent `text/plain` → `apiFetch` détecte le `Content-Type` pour ne pas parser en JSON
- Boutons d'action workflow conditionnels selon l'état courant (`PLAN_REVIEW_NEEDED`, `IMPLEMENTATION_REVIEW_NEEDED`)
- CORS déjà configuré en `*` côté API — aucune modification backend requise

Plan sauvegardé dans `runs/T029/plan.md`, prêt pour review.
