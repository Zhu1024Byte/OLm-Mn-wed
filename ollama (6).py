"""Async HTTP client for the upstream model backend.

Supports two upstream API styles, selected with the ``OLLAMA_API_STYLE``
environment variable:

- ``ollama`` (default): native Ollama REST API (/api/tags, /api/chat, ...)
- ``openai``: OpenAI-compatible endpoints (/v1/models, /v1/chat/completions,
  /v1/embeddings) — works with llama-swap, llama.cpp server, vLLM, etc.

All functions return/consume *Ollama-shaped* data so the rest of the app is
independent of the backend style.
"""

import json
import logging
import subprocess
from typing import AsyncIterator

import httpx

from ..config import settings

logger = logging.getLogger("olmwed.backend")

BASE_URL = settings.ollama_base_url.rstrip("/")
STYLE = settings.ollama_api_style.strip().lower()

_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
_LONG_TIMEOUT = httpx.Timeout(600.0, connect=5.0)


def http_error_detail(exc: httpx.HTTPError, limit: int = 200) -> str:
    """Extract a short human-readable message from any httpx error.

    Safe on streaming responses (never raises) — used by routers to build
    friendly error messages instead of repeating the same try/except.
    """
    if isinstance(exc, httpx.HTTPStatusError):
        try:
            data = exc.response.json()
        except Exception:
            try:
                return exc.response.text[:limit]
            except Exception:
                return f"HTTP {exc.response.status_code}"
        err = data.get("error") or data.get("detail") or data.get("message")
        if isinstance(err, dict):
            err = err.get("message") or err.get("detail") or str(err)
        msg = str(err).strip()[:limit] if err else ""
        prefix = f"HTTP {exc.response.status_code}"
        return f"{prefix}：{msg}" if msg else prefix
    return f"{exc.__class__.__name__}: {exc}"[:limit]


def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


def _unsupported(what: str):
    raise RuntimeError(f"当前模型后端（{STYLE}）不支持{what}")


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------
async def version() -> dict:
    """Return the backend version (best effort)."""
    if STYLE == "openai":
        return {"version": "openai-compatible", "style": "openai"}
    async with httpx.AsyncClient(trust_env=False, timeout=_TIMEOUT) as client:
        resp = await client.get(_url("/api/version"))
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Model listing / status
# ---------------------------------------------------------------------------
async def tags() -> dict:
    """List installed models (Ollama-shaped ``{"models": [...]}``)."""
    if STYLE == "openai":
        async with httpx.AsyncClient(trust_env=False, timeout=_TIMEOUT) as client:
            resp = await client.get(_url("/v1/models"))
            resp.raise_for_status()
            data = resp.json()
        models = []
        for m in data.get("data", []):
            # llama-swap exposes status as {"value": "loaded"|"unloaded"}; normalize to a string
            raw_status = m.get("status")
            if isinstance(raw_status, dict):
                raw_status = raw_status.get("value")
            models.append(
                {
                    "name": m.get("id", ""),
                    "size": None,
                    "modified_at": None,
                    "details": {},
                    "status": raw_status if isinstance(raw_status, str) else None,
                }
            )
        return {"models": models}

    async with httpx.AsyncClient(trust_env=False, timeout=_TIMEOUT) as client:
        resp = await client.get(_url("/api/tags"))
        resp.raise_for_status()
        return resp.json()


async def ps() -> dict:
    """Models currently loaded in memory (best effort)."""
    if STYLE == "openai":
        return {"models": []}
    async with httpx.AsyncClient(trust_env=False, timeout=_TIMEOUT) as client:
        resp = await client.get(_url("/api/ps"))
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Model management
# ---------------------------------------------------------------------------
async def create_model(name: str, modelfile: str) -> dict:
    """``POST /api/create`` — import a model from a Modelfile (Ollama only).

    OpenAI-compatible backends (llama.cpp / llama-swap) have no import API;
    the caller is expected to have saved the GGUF file and should surface the
    ``note`` to the user instead of failing.
    """
    if STYLE == "openai":
        return {
            "status": "saved",
            "note": "文件已保存到模型目录；OpenAI 兼容后端不支持 API 导入，请在模型后端配置中注册该模型后重启",
        }
    async with httpx.AsyncClient(trust_env=False, timeout=_LONG_TIMEOUT) as client:
        resp = await client.post(_url("/api/create"), json={"name": name, "modelfile": modelfile})
        resp.raise_for_status()
        return resp.json()


async def delete_model(name: str) -> dict:
    """Delete a model from the backend.

    - Ollama: ``DELETE /api/delete``.
    - OpenAI-compatible: try ``DELETE /v1/models/{name}``; if the backend does
      not support it (404/405), return ``deleted: False`` with a note so the
      caller can still clean up local files and config.
    """
    if STYLE == "openai":
        from urllib.parse import quote

        async with httpx.AsyncClient(trust_env=False, timeout=_TIMEOUT) as client:
            resp = await client.request("DELETE", _url(f"/v1/models/{quote(name, safe='')}"))
        if resp.status_code < 400:
            return {"deleted": True, "note": "已从模型后端删除"}
        return {
            "deleted": False,
            "note": f"模型后端不支持通过 API 删除（HTTP {resp.status_code}），已清理本地文件与配置",
        }

    async with httpx.AsyncClient(trust_env=False, timeout=_TIMEOUT) as client:
        resp = await client.request("DELETE", _url("/api/delete"), json={"name": name})
        resp.raise_for_status()
        return {"deleted": True, "note": ""}


async def load_model(model: str) -> dict:
    """Trigger loading of a model into memory (for the 加载 button).

    - Ollama: ``POST /api/generate`` with an empty prompt + keep_alive.
    - OpenAI-compatible: send a minimal chat request (llama-swap / llama.cpp
      server load the model on first request).
    """
    if STYLE == "openai":
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": " "}],
            "stream": False,
            "max_tokens": 1,
        }
        async with httpx.AsyncClient(trust_env=False, timeout=_LONG_TIMEOUT) as client:
            resp = await client.post(_url("/v1/chat/completions"), json=payload)
        if resp.status_code >= 400:
            detail = ""
            try:
                err = resp.json().get("error")
                detail = str(err)[:200]
            except Exception:
                try:
                    detail = resp.text[:200]
                except Exception:
                    detail = ""
            raise RuntimeError(f"模型加载失败（HTTP {resp.status_code}）：{detail}")
        return {"status": "loaded"}

    async with httpx.AsyncClient(trust_env=False, timeout=_LONG_TIMEOUT) as client:
        resp = await client.post(
            _url("/api/generate"),
            json={"model": model, "prompt": "", "stream": False, "keep_alive": -1},
        )
        resp.raise_for_status()
        return {"status": "loaded"}


async def unload_model(model: str) -> dict:
    """Unload a model from memory (the 卸下 button).

    - Ollama: ``POST /api/generate`` with ``keep_alive: 0`` unloads at once.
    - OpenAI-compatible (llama-swap): no unload API exists, so we kill the
      llama-server process hosting the model inside the container
      (``pkill -f /models/<file>.gguf``); llama-swap then reports it unloaded.
    """
    if STYLE == "openai":
        filename = _llamaswap_model_file(model)
        if not filename:
            raise RuntimeError("模型不在 llama-swap 配置中，无法卸下")
        # kill 加载该模型的 llama-server 进程（按模型文件路径匹配）
        import shutil

        docker = shutil.which("docker")
        if not docker:
            raise RuntimeError("未检测到 docker，无法卸下模型（请手动停止 llama-swap）")
        proc = subprocess.run(
            [docker, "exec", "llama-swap", "sh", "-c", f"pkill -f {filename}"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # pkill 返回 0=杀到进程, 1=无匹配（模型本就未加载）；两种情况下模型都会变为 unloaded
        logger.info("卸下模型 %s (%s)", model, filename)
        return {"status": "unloaded", "note": "模型已停止并从内存卸下" if proc.returncode == 0 else "模型未在运行（无需卸下）"}

    async with httpx.AsyncClient(trust_env=False, timeout=_LONG_TIMEOUT) as client:
        resp = await client.post(
            _url("/api/generate"),
            json={"model": model, "prompt": "", "stream": False, "keep_alive": 0},
        )
        resp.raise_for_status()
        return {"status": "unloaded"}


def _llamaswap_model_file(model: str) -> str | None:
    """Return the GGUF filename of a model from the llama-swap config (best effort)."""
    try:
        import re

        import yaml  # PyYAML
    except ImportError:
        return None
    import shutil

    docker = shutil.which("docker")
    if not docker:
        return None
    try:
        proc = subprocess.run(
            [docker, "exec", "llama-swap", "cat", "/app/config.yaml"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        cfg = yaml.safe_load(proc.stdout) or {}
    except Exception:
        return None
    entry = (cfg.get("models") or {}).get(model)
    if not entry:
        return None
    cmd = str(entry.get("cmd", ""))
    m = re.search(r"--model\s+([^\s]+)", cmd)
    if not m:
        return None
    # 返回容器内路径 basename，用于 pkill 匹配
    return m.group(1).rsplit("/", 1)[-1]


def backend_label() -> str:
    """Human-readable name of the configured model backend."""
    if STYLE == "openai":
        return "ollama.cpp / llama-swap（OpenAI 兼容）"
    return "Ollama"


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
async def embeddings(model: str, prompt: str) -> list[float]:
    """Embed a single text; returns the vector."""
    if STYLE == "openai":
        async with httpx.AsyncClient(trust_env=False, timeout=_LONG_TIMEOUT) as client:
            resp = await client.post(
                _url("/v1/embeddings"), json={"model": model, "input": prompt}
            )
            resp.raise_for_status()
            data = resp.json()
        items = data.get("data") or []
        if not items or "embedding" not in items[0]:
            raise RuntimeError("后端未返回 embedding")
        return items[0]["embedding"]

    async with httpx.AsyncClient(trust_env=False, timeout=_LONG_TIMEOUT) as client:
        resp = await client.post(
            _url("/api/embeddings"), json={"model": model, "prompt": prompt}
        )
        resp.raise_for_status()
        data = resp.json()
        embedding = data.get("embedding")
        if embedding is None:
            raise RuntimeError("Ollama 未返回 embedding")
        return embedding


# ---------------------------------------------------------------------------
# Chat (payload is Ollama-shaped; converted internally for openai style)
# ---------------------------------------------------------------------------
def _to_openai_chat(payload: dict) -> dict:
    """Convert an Ollama /api/chat payload to an OpenAI chat payload."""
    options = payload.get("options") or {}
    out: dict = {
        "model": payload["model"],
        "messages": payload.get("messages", []),
        "stream": payload.get("stream", False),
    }
    if "temperature" in options:
        out["temperature"] = options["temperature"]
    if options.get("num_predict"):
        out["max_tokens"] = options["num_predict"]
    return out


async def chat_once(payload: dict) -> dict:
    """Full (non-streaming) chat; returns an Ollama-shaped response."""
    if STYLE == "openai":
        openai_payload = _to_openai_chat(payload)
        openai_payload["stream"] = False
        async with httpx.AsyncClient(trust_env=False, timeout=_LONG_TIMEOUT) as client:
            resp = await client.post(_url("/v1/chat/completions"), json=openai_payload)
            resp.raise_for_status()
            data = resp.json()
        usage = data.get("usage") or {}
        return {
            "message": {"role": "assistant", "content": (data.get("choices") or [{}])[0].get("message", {}).get("content", "")},
            "prompt_eval_count": usage.get("prompt_tokens", 0),
            "eval_count": usage.get("completion_tokens", 0),
        }

    async with httpx.AsyncClient(trust_env=False, timeout=_LONG_TIMEOUT) as client:
        resp = await client.post(_url("/api/chat"), json=payload)
        resp.raise_for_status()
        return resp.json()


async def chat_stream(payload: dict) -> AsyncIterator[dict]:
    """Streaming chat; yields Ollama-shaped chunks (``message.content`` / ``done``)."""
    if STYLE == "openai":
        openai_payload = _to_openai_chat(payload)
        openai_payload["stream"] = True
        async with httpx.AsyncClient(trust_env=False, timeout=None) as client:
            async with client.stream("POST", _url("/v1/chat/completions"), json=openai_payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        yield {"message": {"role": "assistant", "content": ""}, "done": True}
                        return
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = ((obj.get("choices") or [{}])[0].get("delta") or {}).get("content") or ""
                    if delta:
                        yield {"message": {"role": "assistant", "content": delta}, "done": False}
        return

    async with httpx.AsyncClient(trust_env=False, timeout=None) as client:
        async with client.stream("POST", _url("/api/chat"), json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("后端返回了非 JSON 行: %.200s", line)


async def generate_stream(payload: dict) -> AsyncIterator[dict]:
    """``POST /api/generate`` with ``stream: true``; yields parsed NDJSON lines.

    OpenAI-style backends expose no /api/generate; this is Ollama-only.
    """
    if STYLE == "openai":
        _unsupported("/api/generate")
    async with httpx.AsyncClient(trust_env=False, timeout=None) as client:
        async with client.stream("POST", _url("/api/generate"), json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("后端返回了非 JSON 行: %.200s", line)
