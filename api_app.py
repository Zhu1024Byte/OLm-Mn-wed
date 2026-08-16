"""OpenAI-compatible API service (runs on port 3001).

Implements a subset of the OpenAI Chat Completions API, backed by Ollama:
- ``POST /v1/chat/completions``  (stream and non-stream)
- ``GET  /v1/models``

Authentication: ``Authorization: Bearer <api_key>`` where the key is an
ApiKey row created in the web UI. The service can be toggled on/off at
runtime via ``data/settings.json`` (api_enabled).
"""

import json
import logging
import time
import uuid
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .config import settings as app_settings
from .database import SessionLocal
from .models import ApiKey
from .services import ollama, runtime_settings

logger = logging.getLogger("olmwed.api")

app = FastAPI(
    title="OLm-Mn-wed OpenAI-compatible API",
    version=app_settings.version,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _authenticate(authorization: str | None) -> None:
    """Validate the Bearer token against the api_keys table."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API key")
    key_value = authorization[len("Bearer ") :].strip()

    db = SessionLocal()
    try:
        row = db.query(ApiKey).filter(ApiKey.key == key_value).first()
        if row is None or not row.enabled:
            raise HTTPException(status_code=401, detail="Invalid or disabled API key")
        row.last_used = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def _require_service_enabled() -> None:
    if not runtime_settings.api_enabled():
        raise HTTPException(
            status_code=403,
            detail="API service is disabled (enable it in the web UI settings)",
        )


def _usage(prompt_tokens: int, completion_tokens: int) -> dict:
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


def _upstream_error(exc: httpx.HTTPStatusError) -> str:
    """Short upstream error for 502 responses (safe on streaming)."""
    detail = ollama.http_error_detail(exc)
    return f"（{detail}）" if detail else ""


# ---------------------------------------------------------------------------
# Schemas (OpenAI-compatible subset)
# ---------------------------------------------------------------------------
class ChatMessage(BaseModel):
    role: str
    content: str

    model_config = {"extra": "ignore"}


class ChatCompletionRequest(BaseModel):
    model: str = Field(min_length=1)
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    stream: bool = False
    max_tokens: int | None = Field(default=None, ge=1)
    # Ollama-specific extras (optional)
    num_ctx: int | None = Field(default=None, ge=256)
    num_gpu: int | None = None
    num_thread: int | None = None
    think: bool | None = None

    model_config = {"extra": "ignore"}


class ModelOut(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "ollama"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "openai-compatible-api"}


@app.get("/v1/models")
async def list_models(request: Request):
    """List models in OpenAI format."""
    _require_service_enabled()
    _authenticate(request.headers.get("authorization"))

    try:
        data = await ollama.tags()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Ollama 不可用：{exc}")

    now = int(time.time())
    models = [
        ModelOut(id=m.get("name") or m.get("model") or "", created=now)
        for m in data.get("models", [])
    ]
    return {"object": "list", "data": models}


@app.post("/v1/chat/completions")
async def chat_completions(payload: ChatCompletionRequest, request: Request):
    """Chat completions, streamed or not, proxied to Ollama."""
    _require_service_enabled()
    _authenticate(request.headers.get("authorization"))

    options: dict = {"temperature": payload.temperature if payload.temperature is not None else 0.7}
    if payload.num_ctx is not None:
        options["num_ctx"] = payload.num_ctx
    if payload.num_gpu is not None:
        options["num_gpu"] = payload.num_gpu
    if payload.num_thread is not None:
        options["num_thread"] = payload.num_thread
    if payload.max_tokens is not None:
        options["num_predict"] = payload.max_tokens

    ollama_payload = {
        "model": payload.model,
        "messages": [m.model_dump() for m in payload.messages],
        "stream": payload.stream,
        "options": options,
    }
    if payload.think is not None:
        ollama_payload["think"] = payload.think

    completion_id = f"chatcmpl-{uuid.uuid4().hex[:16]}"
    created = int(time.time())

    if not payload.stream:
        return await _non_streaming(ollama_payload, payload.model, completion_id, created)

    return await _streaming(ollama_payload, payload.model, completion_id, created)


async def _non_streaming(ollama_payload: dict, model: str, completion_id: str, created: int):
    """Full-response path (stream: false)."""
    try:
        data = await ollama.chat_once(ollama_payload)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"模型后端错误（HTTP {exc.response.status_code}）{_upstream_error(exc)}",
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"无法连接模型后端：{exc}")

    content = (data.get("message") or {}).get("content") or ""
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": _usage(
            int(data.get("prompt_eval_count", 0)),
            int(data.get("eval_count", len(content) // 4)),
        ),
    }


async def _streaming(ollama_payload: dict, model: str, completion_id: str, created: int):
    """SSE path (stream: true) — OpenAI ``chat.completion.chunk`` events."""

    def chunk_event(delta: str, finish: str | None = None) -> str:
        data = {
            "id": completion_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [{"index": 0, "delta": {"content": delta}, "finish_reason": finish}],
        }
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    async def event_gen():
        try:
            async for part in ollama.chat_stream(ollama_payload):
                piece = (part.get("message") or {}).get("content") or ""
                if piece:
                    yield chunk_event(piece)
                if part.get("done"):
                    yield chunk_event("", "stop")
                    yield "data: [DONE]\n\n"
                    return
        except httpx.HTTPStatusError as exc:
            msg = f"模型后端错误（HTTP {exc.response.status_code}）{_upstream_error(exc)}"
            yield f"data: {json.dumps({'error': {'message': msg}})}\n\n"
        except httpx.HTTPError as exc:
            yield f"data: {json.dumps({'error': {'message': f'无法连接模型后端：{exc}'}})}\n\n"

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
