"""Runtime settings registry (T215).

V1 of the Global Runtime Settings layer. Holds the catalogue of admin-tunable
settings and resolves each one through a three-level precedence chain:

    Runtime Settings DB  →  os.environ (env_var fallback)  →  hardcoded default

Sensitive keys (``is_sensitive=True``) are NEVER persisted in the DB in V1.
Encryption-at-rest and rotation are out of scope; the registry reports them
solely as ``configured`` / ``not_configured`` status indicators derived from the
process environment.

This module deliberately keeps no in-process cache. ``get_setting`` re-queries
the DB on every call so that "change value → save → new value immediately
available" works without an invalidation bus. Tight inner loops are not in
scope for V1.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402


SETTING_VALUE_TYPES = ("string", "int", "float", "bool", "secret")


@dataclass(frozen=True)
class SettingSpec:
    """Static declaration of a registered setting.

    Attributes:
        key: Canonical setting name (also the API path segment).
        value_type: One of ``SETTING_VALUE_TYPES``. Drives coercion and the
            shape of the UI editor.
        description: Short human-readable line surfaced in the UI.
        is_sensitive: Secrets — never returned as raw values, never persisted
            in V1 (see module docstring).
        requires_restart: True when the consumer reads the value at start-up
            and won't pick up live changes. The API still accepts writes; the
            UI shows a ``Restart required`` badge.
        default: Hardcoded fallback used when neither the DB nor env supplies
            a value.
        env_var: The ``.env`` variable this setting maps to. None when there
            is no existing environment fallback.
        coerce: Optional override of the default value-type coercion.
    """

    key: str
    value_type: str
    description: str
    is_sensitive: bool = False
    requires_restart: bool = False
    default: Any = None
    env_var: str | None = None
    coerce: Callable[[Any], Any] | None = None


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "on"}:
        return True
    if text in {"false", "0", "no", "off", ""}:
        return False
    raise ValueError(f"cannot coerce {value!r} to bool")


def _coerce_for_type(value_type: str, value: Any) -> Any:
    if value is None:
        return None
    if value_type == "string" or value_type == "secret":
        return str(value)
    if value_type == "int":
        return int(value)
    if value_type == "float":
        return float(value)
    if value_type == "bool":
        return _coerce_bool(value)
    raise ValueError(f"unknown value_type {value_type!r}")


SETTING_SPECS: dict[str, SettingSpec] = {
    "DEFAULT_PLANNER_MODEL": SettingSpec(
        key="DEFAULT_PLANNER_MODEL",
        value_type="string",
        description="Default model used by the planner agent.",
        default="balanced-code-model",
        env_var="DEFAULT_PLANNER_MODEL",
    ),
    "DEFAULT_CODER_MODEL": SettingSpec(
        key="DEFAULT_CODER_MODEL",
        value_type="string",
        description="Default model used by the coder agent.",
        default="balanced-code-model",
        env_var="DEFAULT_CODER_MODEL",
    ),
    "DEFAULT_REVIEWER_MODEL": SettingSpec(
        key="DEFAULT_REVIEWER_MODEL",
        value_type="string",
        description="Default model used by the reviewer agent.",
        default="balanced-code-model",
        env_var="DEFAULT_REVIEWER_MODEL",
    ),
    "DEFAULT_TESTER_MODEL": SettingSpec(
        key="DEFAULT_TESTER_MODEL",
        value_type="string",
        description="Default model used by the tester agent.",
        default="balanced-code-model",
        env_var="DEFAULT_TESTER_MODEL",
    ),
    "MAX_WORKERS": SettingSpec(
        key="MAX_WORKERS",
        value_type="int",
        description="Maximum concurrent ticket workers the daemon will launch.",
        default=1,
        env_var="DAEMON_MAX_WORKERS",
        # Daemon pool size is read once at start via the --max-workers CLI arg.
        # Live changes are not picked up until the daemon restarts.
        requires_restart=True,
    ),
    "INTELLIGENCE_TIMEOUT_SECONDS": SettingSpec(
        key="INTELLIGENCE_TIMEOUT_SECONDS",
        value_type="int",
        description="Upper bound on the ticket intelligence AI subprocess (seconds).",
        default=120,
        env_var="AI_DEV_FACTORY_INTEL_TIMEOUT",
    ),
    "DISPATCHER_ENABLED": SettingSpec(
        key="DISPATCHER_ENABLED",
        value_type="string",
        description=(
            "Ticket dispatcher mode: one of off | advisory | manual | auto."
        ),
        default="off",
        env_var="AI_DEV_FACTORY_DISPATCHER_MODE",
    ),
    "LOG_LEVEL": SettingSpec(
        key="LOG_LEVEL",
        value_type="string",
        description="Root logging level for the control API.",
        default="INFO",
        env_var="LOG_LEVEL",
    ),
    # Sensitive keys: V1 reports configured / not_configured only and never
    # accepts writes. Encryption-at-rest is a separate ticket.
    "OPENAI_API_KEY": SettingSpec(
        key="OPENAI_API_KEY",
        value_type="secret",
        description="OpenAI API key (status indicator only — read-only in V1).",
        is_sensitive=True,
        env_var="OPENAI_API_KEY",
    ),
    "ANTHROPIC_API_KEY": SettingSpec(
        key="ANTHROPIC_API_KEY",
        value_type="secret",
        description="Anthropic API key (status indicator only — read-only in V1).",
        is_sensitive=True,
        env_var="ANTHROPIC_API_KEY",
    ),
    "GITHUB_TOKEN": SettingSpec(
        key="GITHUB_TOKEN",
        value_type="secret",
        description="GitHub token (status indicator only — read-only in V1).",
        is_sensitive=True,
        env_var="GITHUB_TOKEN",
    ),
}


class UnknownSettingError(KeyError):
    """Raised when an operation targets a key not in ``SETTING_SPECS``."""


class SensitiveSettingWriteError(PermissionError):
    """Raised when a write is attempted on an ``is_sensitive`` key.

    V1 does not persist secret values to the DB. Sensitive settings are
    surfaced as status indicators only; writing them must be rejected by both
    the registry and the API layer.
    """


def _get_spec(key: str) -> SettingSpec:
    spec = SETTING_SPECS.get(key)
    if spec is None:
        raise UnknownSettingError(key)
    return spec


def _coerce_value(spec: SettingSpec, value: Any) -> Any:
    if spec.coerce is not None:
        return spec.coerce(value)
    return _coerce_for_type(spec.value_type, value)


def _env_value(spec: SettingSpec) -> str | None:
    """Return the raw environment value when ``env_var`` is set & present."""
    if not spec.env_var:
        return None
    raw = os.environ.get(spec.env_var)
    if raw is None or raw == "":
        return None
    return raw


def get_setting(db_path, key: str) -> Any:
    """Resolve the effective in-process value for ``key``.

    Precedence: DB row → ``os.environ[env_var]`` → ``default``.
    Sensitive keys never read from the DB (they are not persisted in V1) and
    return the raw environment value so existing call sites continue to work
    unchanged.
    """
    spec = _get_spec(key)

    if not spec.is_sensitive:
        try:
            row = runtime_db.get_runtime_setting(db_path, key)
        except Exception:
            row = None
        if row is not None and row.get("value") is not None:
            try:
                return _coerce_value(spec, row["value"])
            except (TypeError, ValueError):
                # Bad data in the DB falls through to env/default rather than
                # raising at consumer call sites.
                pass

    env_raw = _env_value(spec)
    if env_raw is not None:
        try:
            return _coerce_value(spec, env_raw)
        except (TypeError, ValueError):
            pass

    return spec.default


def _source_for(db_row: dict | None, env_raw: str | None) -> str:
    if db_row is not None:
        return "db"
    if env_raw is not None:
        return "env"
    return "default"


def resolve_effective_setting(db_path, key: str) -> dict:
    """Return the canonical API row for ``key``.

    Sensitive keys never reveal their raw value: ``value`` is replaced with
    ``configured`` or ``not_configured`` derived from the process environment.
    """
    spec = _get_spec(key)
    db_row = None
    if not spec.is_sensitive:
        try:
            db_row = runtime_db.get_runtime_setting(db_path, key)
        except Exception:
            db_row = None
    env_raw = _env_value(spec)
    source = _source_for(db_row, env_raw)

    if spec.is_sensitive:
        value: Any = "configured" if env_raw is not None else "not_configured"
        updated_at = None
        updated_by = None
        editable = False
    else:
        if db_row is not None and db_row.get("value") is not None:
            try:
                value = _coerce_value(spec, db_row["value"])
            except (TypeError, ValueError):
                value = spec.default if env_raw is None else _safe_coerce(spec, env_raw)
        elif env_raw is not None:
            value = _safe_coerce(spec, env_raw)
        else:
            value = spec.default
        updated_at = db_row.get("updated_at") if db_row else None
        updated_by = db_row.get("updated_by") if db_row else None
        editable = True

    return {
        "key": spec.key,
        "value": value,
        "value_type": spec.value_type,
        "source": source,
        "description": spec.description,
        "is_sensitive": spec.is_sensitive,
        "requires_restart": spec.requires_restart,
        "editable": editable,
        "updated_at": updated_at,
        "updated_by": updated_by,
    }


def _safe_coerce(spec: SettingSpec, value: Any) -> Any:
    try:
        return _coerce_value(spec, value)
    except (TypeError, ValueError):
        return spec.default


def list_effective_settings(db_path) -> list[dict]:
    """Return one effective row per declared key, ordered by ``SETTING_SPECS``."""
    return [resolve_effective_setting(db_path, key) for key in SETTING_SPECS]


def set_setting(db_path, key: str, value: Any, *, updated_by: str | None = None) -> dict:
    """Persist a DB override for ``key``. Rejects sensitive keys.

    Raises:
        UnknownSettingError: ``key`` is not registered.
        SensitiveSettingWriteError: ``key`` is flagged sensitive (V1: read-only).
        ValueError / TypeError: ``value`` cannot be coerced to ``value_type``.
    """
    spec = _get_spec(key)
    if spec.is_sensitive:
        raise SensitiveSettingWriteError(
            f"setting {key!r} is sensitive; secret editing is not supported in V1"
        )
    coerced = _coerce_value(spec, value)
    stored = _stringify_for_storage(spec.value_type, coerced)
    runtime_db.upsert_runtime_setting(
        db_path,
        key,
        value=stored,
        value_type=spec.value_type,
        scope="global",
        description=spec.description,
        is_sensitive=spec.is_sensitive,
        requires_restart=spec.requires_restart,
        updated_by=updated_by,
    )
    return resolve_effective_setting(db_path, key)


def delete_setting(db_path, key: str) -> None:
    """Remove the DB override for ``key`` so resolution falls back to env/default."""
    spec = _get_spec(key)
    if spec.is_sensitive:
        # Sensitive keys are never persisted in V1; deletion is a no-op rather
        # than an error so the API can offer a uniform "reset" action.
        return
    runtime_db.delete_runtime_setting(db_path, key)


def _stringify_for_storage(value_type: str, value: Any) -> str:
    if value_type == "bool":
        return "true" if value else "false"
    return str(value)


__all__ = [
    "SettingSpec",
    "SETTING_SPECS",
    "SETTING_VALUE_TYPES",
    "UnknownSettingError",
    "SensitiveSettingWriteError",
    "get_setting",
    "resolve_effective_setting",
    "list_effective_settings",
    "set_setting",
    "delete_setting",
]
