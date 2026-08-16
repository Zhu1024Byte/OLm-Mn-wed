"""Version check: compare local Ollama / this project against GitHub releases."""

import logging
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..config import settings
from ..models import User
from ..services import ollama

logger = logging.getLogger("olmwed.update")
router = APIRouter()

GITHUB_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


def _parse_version(v: str) -> tuple:
    """Parse 'v1.2.3' -> (1, 2, 3); tolerant of suffixes."""
    v = (v or "").lstrip("vV")
    parts = []
    for seg in v.split(".")[:3]:
        try:
            parts.append(int("".join(ch for ch in seg if ch.isdigit())))
        except ValueError:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


async def _github_latest(repo: str) -> dict:
    """Query the latest release of a GitHub repo."""
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    try:
        async with httpx.AsyncClient(timeout=GITHUB_TIMEOUT, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return {"latest": None, "url": f"https://github.com/{repo}/releases", "note": f"GitHub 返回 HTTP {resp.status_code}"}
            data = resp.json()
            return {
                "latest": data.get("tag_name"),
                "url": data.get("html_url") or f"https://github.com/{repo}/releases",
                "note": None,
            }
    except httpx.HTTPError as exc:
        return {"latest": None, "url": f"https://github.com/{repo}/releases", "note": f"无法访问 GitHub：{exc.__class__.__name__}"}


@router.get("/check", summary="检查更新")
async def check_update(_: User = Depends(get_current_user)):
    """Compare the running Ollama version and this project against GitHub."""
    result: dict = {
        "ollama": {"current": None, "latest": None, "up_to_date": None, "url": None, "note": None},
        "project": {"current": settings.version, "latest": None, "up_to_date": None, "url": None, "note": None},
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }

    # --- Ollama current version (from the local Ollama service) ---
    try:
        ver = await ollama.version()
        result["ollama"]["current"] = ver.get("version")
        result["ollama"]["url"] = "https://github.com/ollama/ollama/releases"
        latest = await _github_latest("ollama/ollama")
        result["ollama"]["latest"] = latest.get("latest")
        result["ollama"]["note"] = latest.get("note")
        if result["ollama"]["current"] and result["ollama"]["latest"]:
            result["ollama"]["up_to_date"] = _parse_version(result["ollama"]["current"]) >= _parse_version(result["ollama"]["latest"])
    except httpx.HTTPError:
        result["ollama"]["note"] = "无法连接本地 Ollama 服务，跳过 Ollama 版本检查"

    # --- This project (repo configurable via PROJECT_REPO, e.g. "user/olm-mn-wed") ---
    if settings.project_repo:
        latest = await _github_latest(settings.project_repo)
        result["project"]["latest"] = latest.get("latest")
        result["project"]["url"] = latest.get("url")
        result["project"]["note"] = latest.get("note")
        if result["project"]["latest"]:
            result["project"]["up_to_date"] = _parse_version(result["project"]["current"]) >= _parse_version(result["project"]["latest"])
    else:
        result["project"]["note"] = "未配置项目仓库（环境变量 PROJECT_REPO），跳过项目版本检查"

    return result
