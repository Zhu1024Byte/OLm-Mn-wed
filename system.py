"""System information and model-backend operations (restart / stop / start)."""

import logging
import shutil
import subprocess

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..auth import get_current_user
from ..config import settings
from ..models import User
from ..services import ollama

logger = logging.getLogger("olmwed.system")
router = APIRouter()


class BackendAction(BaseModel):
    action: str = Field(pattern="^(restart|stop|start)$")


def _find_compose_file() -> str | None:
    """Locate a docker-compose file that manages the ollama service."""
    candidates = [
        "/app/docker-compose.yml",
        "docker-compose.yml",
        "/root/OLm-Mn-wed/docker-compose.yml",
    ]
    for c in candidates:
        if c.startswith("/") and __import__("os").path.isfile(c):
            return c
    return None


def _backend_container() -> str:
    """Best-effort container name for the model backend."""
    return "llama-swap" if settings.ollama_api_style.strip().lower() == "openai" else "ollama"


@router.get("/info", summary="系统信息")
def system_info(_: User = Depends(get_current_user)):
    """Return app + model backend information."""
    return {
        "version": settings.version,
        "backend_style": settings.ollama_api_style,
        "backend_label": ollama.backend_label(),
        "backend_url": settings.ollama_base_url,
        "embed_model": settings.embed_model,
    }


@router.get("/status", summary="后端健康状态")
async def system_status(_: User = Depends(get_current_user)):
    """Backend reachability + model overview for the UI status indicator."""
    backend_ok = False
    total = loaded = 0
    try:
        data = await ollama.tags()
        total = len(data.get("models", []))
        loaded = sum(1 for m in data.get("models", []) if m.get("status") == "loaded")
        backend_ok = True
    except Exception:  # noqa: BLE001 — any failure just means "backend down"
        backend_ok = False
    return {
        "backend_ok": backend_ok,
        "backend_label": ollama.backend_label(),
        "backend_url": settings.ollama_base_url,
        "models": total,
        "loaded": loaded,
        "version": settings.version,
    }


@router.post("/backend/action", summary="模型后端操作")
def backend_action(
    payload: BackendAction,
    _: User = Depends(get_current_user),
):
    """Restart / stop / start the model backend container.

    Works when this app runs on the host (native deployment) with docker
    access; inside the webapp container (docker deployment) it will fail with
    a clear message.
    """
    action = payload.action
    docker = shutil.which("docker")
    if not docker:
        raise HTTPException(status_code=501, detail="未找到 docker 命令（webapp 容器内不可用，请在宿主机操作）")

    if settings.ollama_api_style.strip().lower() == "openai":
        # OpenAI-compatible backend: manage the llama-swap container by name
        cmd = f"{docker} {action} llama-swap"
        label = "llama-swap"
    else:
        # Ollama backend: use docker compose when a compose file is available
        compose = _find_compose_file()
        if compose:
            cmd = f"{docker} compose -f {compose} {action} ollama"
        else:
            cmd = f"{docker} {action} ollama"
        label = "ollama"

    logger.info("backend action: %s %s", action, label)
    try:
        proc = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=120
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"{label} {action} 超时")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"执行失败：{exc}")

    output = (proc.stdout or "")[-800:] + (proc.stderr or "")[-800:]
    if proc.returncode != 0:
        raise HTTPException(status_code=502, detail=f"{label} {action} 失败：{output.strip()}")
    return {"action": action, "backend": label, "status": "ok", "output": output.strip()}
