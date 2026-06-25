# Plan fix — make secrets read-only in V1 and clarify global Postgres scope

## Required plan update

Update `runs/T215/plan.md` before implementation.

The current plan must be corrected in two areas:

1. sensitive settings must not be stored in plaintext in V1;
2. Postgres storage for `runtime_settings` must be explicitly global-only.

## 1. Sensitive settings in V1

T215 V1 must not persist secret values in the database unless encrypted-at-rest secret storage is implemented.

For this ticket, do not implement encryption.

Therefore, sensitive settings must be **read-only status indicators**.

Sensitive keys include:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GITHUB_TOKEN
```

### Required V1 behavior

For sensitive settings:

```text
GET /api/settings
GET /api/settings/{key}
```

must return:

```text
value = configured | not_configured
source = env | default
is_sensitive = true
editable = false
```

The value must be derived from the existing environment/process configuration.

The API and UI must never display the raw value.

### Required API behavior

For sensitive settings:

```text
PUT /api/settings/{secret_key}
```

should either:

```text
return 403/422 with message: Secret editing is not supported in V1
```

or be omitted/disabled for sensitive rows.

Do not write secret values to `runtime_settings` in V1.

### Required UI behavior

Sensitive rows must show:

```text
configured / not_configured
```

and must be non-editable in V1.

A small helper text is acceptable:

```text
Secret replacement will be supported in a future encrypted secret-management ticket.
```

### Remove from the plan

Remove any acceptance criteria that says:

```text
PUT /api/settings/OPENAI_API_KEY accepts a value
```

Replace it with:

```text
PUT /api/settings/OPENAI_API_KEY is rejected or disabled in V1, and no raw secret is persisted.
```

## 2. Postgres global-only runtime_settings storage

T215 V1 supports only:

```text
scope = global
```

The Postgres implementation must therefore be unambiguous and not require a project id in public helper signatures.

### Preferred Postgres schema for V1

Use a simple global table matching SQLite semantics:

```sql
CREATE TABLE IF NOT EXISTS runtime_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL,
    scope TEXT NOT NULL DEFAULT 'global',
    description TEXT,
    is_sensitive BOOLEAN NOT NULL DEFAULT FALSE,
    requires_restart BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TEXT NOT NULL,
    updated_by TEXT
);
```

All helpers remain:

```text
list_runtime_settings(db_path)
get_runtime_setting(db_path, key)
upsert_runtime_setting(db_path, key, ...)
delete_runtime_setting(db_path, key)
```

without a project_id argument.

### Alternative acceptable strategy

If the repository architecture strongly requires a `project_id` column in Postgres, the plan must specify:

```text
project_id = '__global__'
```

for all V1 runtime settings and all helpers must hardcode/use this sentinel internally.

But the preferred V1 approach is **no project_id column** for `runtime_settings`.

## Tests / acceptance criteria updates

Update tests and acceptance criteria to include:

- Sensitive settings are listed as `configured` / `not_configured` only.
- Sensitive settings are not editable in V1.
- `PUT` on a sensitive key returns an explicit rejection if the endpoint is reachable.
- No secret value is stored in the `runtime_settings` table.
- SQLite and Postgres runtime settings tables expose the same public global behavior.
- Postgres helpers work without requiring project id input.
- `get_setting(db_path, key)` remains backend-agnostic.

## Non-goals

Keep these out of T215:

- encrypted secret storage
- secret rotation
- audit log for secret changes
- project-scoped settings
- automatic restart orchestration

## Review verdict after fix

Once the plan is updated with these corrections, it can be reviewed again for approval.
