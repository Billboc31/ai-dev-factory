# T216 — Fix Global Settings page empty when no runtime settings overrides exist

**Source**: GitHub Issue #288

## Description

The Global Settings page is empty on a fresh installation because GET /api/settings returns an empty list when the runtime_settings table contains no rows.

Expected behavior:
- GET /api/settings should always return all entries from SETTING_SPECS.
- Values should be resolved using: DB override > env > default.
- The dashboard table should never be empty when SETTING_SPECS contains entries.

Acceptance criteria:
- Fresh installation displays all settings.
- Empty runtime_settings table still returns effective settings.
- Source column shows env/default when no DB override exists.
- After saving a setting, source changes to db.
- Add tests covering the empty table scenario.
