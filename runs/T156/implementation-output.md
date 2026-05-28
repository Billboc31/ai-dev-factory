Both fixes are correct. Here's what changed in `SandboxRunsTable.jsx`:

1. **Refresh button** (line 224-229) — added as the first action button in `EnvironmentCard`, calls `onRefresh?.()` which is wired to `onDeleted` from the parent, triggering a data refetch.

2. **CopyButton `.catch()`** (lines 52-54) — clipboard promise now has an error handler; silently resets `copied` state if the clipboard API is unavailable (e.g. non-HTTPS context).
