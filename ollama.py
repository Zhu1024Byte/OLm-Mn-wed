"""Ollama proxy endpoints.

Stage 3 scope: model listing (needed by the chat model picker) and running
models. Model import / delete / config lives in stage 4.
"""

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import ModelConfig, User
from ..services import ollama

router = APIRouter()


@router.get("/tags", summary="已安装模型列表")
async def list_models(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List installed models from Ollama, enriched with saved per-model config."""
    try:
        data = await ollama.tags()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"无法连接 Ollama 服务（{exc}），请确认 ollama 容器已启动",
        )

    configs = {c.model_name: c for c in db.query(ModelConfig).all()}
    models = []
    for m in data.get("models", []):
        name = m.get("name") or m.get("model") or ""
        cfg = configs.get(name)
        models.append(
            {
                "name": name,
                "size": m.get("size"),
                "modified_at": m.get("modified_at"),
                "details": m.get("details", {}),
                "status": m.get("status"),
                "config": {
                    "num_ctx": cfg.num_ctx if cfg else None,
                    "num_gpu": cfg.num_gpu if cfg else None,
                    "num_thread": cfg.num_thread if cfg else None,
                    "temperature": cfg.temperature if cfg else None,
                    "system_prompt": cfg.system_prompt if cfg else "",
                },
            }
        )
    return {"models": models}


@router.get("/ps", summary="正在运行的模型")
async def running_models(_: User = Depends(get_current_user)):
    """List models currently loaded in memory (Ollama /api/ps)."""
    try:
        return await ollama.ps()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"无法连接 Ollama 服务（{exc}），请确认 ollama 容器已启动",
        )
