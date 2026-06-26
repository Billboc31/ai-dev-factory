"""Global Runtime Settings routes (T215).

Endpoints
---------

``GET    /api/settings``           — list every declared setting, redacted for
                                     sensitive keys.
``GET    /api/settings/{key}``     — one setting, redacted for sensitive keys.
``PUT    /api/settings/{key}``     — persist a DB override. Sensitive keys are
                                     rejected with 403 (V1 stores no secrets).
``DELETE /api/settings/{key}``     — drop the DB override; resolution falls
                                     back to env / hardcoded default.

The settings layer is global. ``scope='global'`` is the only supported value
in V1; project-scoped settings are out of scope.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ..models.schemas import (
    RuntimeSetting,
    RuntimeSettingUpdate,
    RuntimeSettingsListResponse,
)

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_settings as _runtime_settings  # noqa: E402

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/api/settings", tags=["settings"])


def _db_path(request: Request):
    db = getattr(request.app.state, "db_path", None)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")
    return db


def _row_to_model(row: dict) -> RuntimeSetting:
    return RuntimeSetting(**row)


@router.get("", response_model=RuntimeSettingsListResponse)
def list_settings(request: Request) -> RuntimeSettingsListResponse:
    """List every declared setting.

    Invariant: always returns ``len(SETTING_SPECS)`` entries; the response is
    never DB-filtered. An empty ``runtime_settings`` table is normal on a fresh
    install — rows resolve through env / hardcoded defaults.
    """
    logger.info("api: GET /api/settings")
    db = _db_path(request)
    try:
        rows = _runtime_settings.list_effective_settings(db)
    except Exception:
        # The resolver is supposed to swallow per-key DB failures and fall back
        # to env/default. Anything reaching this point is a real bug — surface
        # it (500) instead of silently returning {"settings": []}.
        logger.exception("api: list_effective_settings failed")
        raise HTTPException(status_code=500, detail="failed to list settings")
    return RuntimeSettingsListResponse(settings=[_row_to_model(r) for r in rows])


@router.get("/{key}", response_model=RuntimeSetting)
def get_setting(key: str, request: Request) -> RuntimeSetting:
    logger.info("api: GET /api/settings/%s", key)
    db = _db_path(request)
    try:
        row = _runtime_settings.resolve_effective_setting(db, key)
    except _runtime_settings.UnknownSettingError:
        raise HTTPException(status_code=404, detail=f"unknown setting {key!r}")
    return _row_to_model(row)


@router.put("/{key}", response_model=RuntimeSetting)
def put_setting(
    key: str,
    payload: RuntimeSettingUpdate,
    request: Request,
) -> RuntimeSetting:
    logger.info("api: PUT /api/settings/%s", key)
    db = _db_path(request)
    try:
        row = _runtime_settings.set_setting(
            db, key, payload.value, updated_by=payload.updated_by
        )
    except _runtime_settings.UnknownSettingError:
        raise HTTPException(status_code=404, detail=f"unknown setting {key!r}")
    except _runtime_settings.SensitiveSettingWriteError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=f"invalid value for {key!r}: {exc}")
    return _row_to_model(row)


@router.delete("/{key}", status_code=204)
def delete_setting(key: str, request: Request) -> None:
    logger.info("api: DELETE /api/settings/%s", key)
    db = _db_path(request)
    try:
        _runtime_settings.delete_setting(db, key)
    except _runtime_settings.UnknownSettingError:
        raise HTTPException(status_code=404, detail=f"unknown setting {key!r}")
    return None
