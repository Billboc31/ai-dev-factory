# Plan Fix — Resolve T178 Merge Conflict

## Problem

The T178 branch conflicts with `main` because `main` already contains part of the T177 supervisor fix.

`main` already has:

```python
class EnvironmentProvisionRequest(BaseModel):
    env_name: str
    project_root: str
    ref: str | None = None
    ref_type: str | None = None
    env_type: str | None = None
    deployment_mode: str | None = None
    web_host: str | None = None
    api_host: str | None = None
    sandbox_path: str | None = None
    runtime_root: str | None = None
    force_source_refresh: bool = False
```

and validation inside `environments_provision` returning HTTP 400 for invalid `runtime_root`.

The T178 branch re-adds the same fields and changes validation to HTTP 422, which creates an unnecessary conflict.

## Required resolution

Resolve the conflict by keeping `main` behavior and adding only the missing diagnostic log from T178.

## `services/supervisor/main.py`

In `environments_provision`, keep the `main` version of:

```python
if body.runtime_root is not None:
    rt = Path(body.runtime_root)
    if not rt.is_absolute() or any(part == ".." for part in rt.parts):
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": "runtime_root: must be an absolute path without '..'"},
        )
```

Do not change it to 422.

Add this log immediately before the validation block:

```python
logger.info(
    "supervisor: provision request env_name=%s project_root=%s runtime_root=%s force_source_refresh=%s",
    body.env_name,
    body.project_root,
    "<set>" if body.runtime_root else None,
    body.force_source_refresh,
)
```

## Tests

If T178 tests expect 422 for invalid runtime_root, update them to expect 400 because `main` already standardized this validation as a bad request.

## Acceptance criteria

- Branch merges cleanly with `main`.
- `EnvironmentProvisionRequest` still contains `runtime_root` and `force_source_refresh`.
- Invalid runtime_root returns 400.
- Provision log includes whether runtime_root was provided.
- Existing T178 runtime_root propagation test still passes.