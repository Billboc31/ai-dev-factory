# Plan review — secrets handling and Postgres global scope

The T215 plan is strong overall: it introduces a runtime settings registry, DB-backed overrides, `.env` fallback, hot-reload semantics for supported values, a Control API surface, and a dashboard Global Settings page.

However, two points must be corrected before implementation starts.

## 1. Secrets must not be stored in plaintext in V1

The current plan says that sensitive values are stored in the DB in plain text and redacted only in the API/UI.

For V1, this is too risky.

Sensitive keys such as:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GITHUB_TOKEN
```

must be read-only status indicators in V1.

Expected V1 behavior:

```text
- show configured / not_configured
- derive status from existing .env / process environment
- never reveal raw values
- do not persist secret values in runtime_settings
- do not add secret replacement in V1 unless encrypted storage is implemented
```

Secret editing/rotation should be deferred to a dedicated future ticket with encryption-at-rest and audit behavior.

## 2. Postgres runtime_settings scope must be global-only and unambiguous

The current plan proposes a Postgres table with composite key:

```text
(project_id, key)
```

but T215 V1 explicitly supports only:

```text
scope = global
```

This creates ambiguity for helpers such as:

```text
get_runtime_setting(db_path, key)
upsert_runtime_setting(db_path, key, ...)
```

because they do not receive a `project_id`.

The corrected plan must choose one explicit global-only Postgres strategy, such as:

```text
key TEXT PRIMARY KEY
```

or, if a project_id column must be kept for backend consistency:

```text
project_id TEXT NOT NULL DEFAULT '__global__'
PRIMARY KEY (project_id, key)
```

with all helpers always using `project_id='__global__'` in V1.

The preferred V1 option is a simple global table keyed by `key`, matching SQLite semantics.

## Review verdict

PLAN_FIX_REQUIRED until:

1. secrets are read-only status indicators in V1 and are not persisted in plaintext;
2. the Postgres schema/helper design is explicitly global-only and unambiguous.
