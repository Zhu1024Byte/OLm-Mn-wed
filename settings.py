"""Application settings endpoints (API service toggle & port)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..config import settings as app_settings
from ..models import User
from ..services import runtime_settings

router = APIRouter()


class SettingsUpdate(BaseModel):
    api_enabled: bool | None = None
    api_port: int | None = Field(default=None, ge=1024, le=65535)


@router.get("", summary="读取应用设置")
def get_settings(_: User = Depends(get_current_user)):
    """Return effective runtime settings (API toggle, ports)."""
    rt = runtime_settings.load()
    return {
        "api_enabled": rt.get("api_enabled", app_settings.api_enabled),
        "api_port": rt.get("api_port", app_settings.api_port),
        "web_port": app_settings.web_port,
    }


@router.patch("", summary="更新应用设置")
def update_settings(
    payload: SettingsUpdate,
    _: User = Depends(get_current_user),
):
    """Update runtime settings.

    - ``api_enabled`` takes effect immediately.
    - ``api_port`` takes effect after the container restarts.
    """
    rt = runtime_settings.load()
    if payload.api_enabled is not None:
        rt["api_enabled"] = payload.api_enabled
    if payload.api_port is not None:
        rt["api_port"] = payload.api_port
    runtime_settings.save(rt)
    return {
        "api_enabled": rt.get("api_enabled", app_settings.api_enabled),
        "api_port": rt.get("api_port", app_settings.api_port),
        "web_port": app_settings.web_port,
    }
