"""Chat endpoints: conversation CRUD + SSE streaming chat via Ollama.

Streaming protocol (text/event-stream, one event per ``data: {...}\\n\\n``):
- ``{"type": "delta", "content": "..."}``  — a piece of the assistant reply
- ``{"type": "done", "content": "...", "conversation_id": N, "model": "..."}``
- ``{"type": "error", "message": "..."}``
"""

import json
import logging
from datetime import datetime

import httpx
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import SessionLocal, get_db
from ..models import Conversation, Message, ModelConfig, User, utcnow
from ..services import ollama
from ..services.knowledge import retrieve_chunks

logger = logging.getLogger("olmwed.chat")
router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ConversationOut(BaseModel):
    id: int
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    role: str
    content: str
    model: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationOut):
    messages: list[MessageOut] = []


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=255)


class ConversationRename(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class ChatRequest(BaseModel):
    conversation_id: int
    model: str = Field(min_length=1, max_length=255)
    # regenerate 时 content 可为空（用历史消息重新生成）
    content: str = Field(default="", max_length=20000)
    # regenerate=true: 不新增 user 消息，删除最后一条 assistant 回复并用现有历史重新生成
    regenerate: bool = False
    # Overrides; when None the saved model_config is used as fallback
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    num_ctx: int | None = Field(default=None, ge=256, le=131072)
    num_gpu: int | None = None
    num_thread: int | None = None
    # Reasoning (Qwen3 / DeepSeek style models)
    think: bool | None = None
    reasoning_effort: str | None = Field(default=None, max_length=32)
    # System prompt; empty string means "no system prompt"
    system_prompt: str = ""
    # Knowledge bases to retrieve from (RAG, stage 5)
    knowledge_ids: list[int] = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"


def _get_owned_conversation(db: Session, cid: int, user: User) -> Conversation:
    conv = db.get(Conversation, cid)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="会话不存在")
    return conv


def _build_ollama_payload(
    req: ChatRequest,
    history: list[Message],
    cfg: ModelConfig | None,
    rag_context: str = "",
) -> dict:
    """Assemble the /api/chat payload from request, history and saved config.

    ``rag_context`` (optional) holds retrieved knowledge-base chunks which are
    injected as an additional system message.
    """
    messages: list[dict] = []

    system_prompt = req.system_prompt.strip() or (cfg.system_prompt.strip() if cfg else "") or ""
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if rag_context:
        messages.append(
            {
                "role": "system",
                "content": (
                    "以下是知识库检索到的参考资料，请优先依据这些内容回答"
                    "（若与问题无关可忽略）：\n\n"
                    f"{rag_context}"
                ),
            }
        )

    for m in history:
        messages.append({"role": m.role, "content": m.content})

    options: dict = {
        "temperature": req.temperature if req.temperature is not None else (cfg.temperature if cfg else 0.7),
        "num_ctx": req.num_ctx if req.num_ctx is not None else (cfg.num_ctx if cfg else 4096),
    }
    if req.num_gpu is not None:
        options["num_gpu"] = req.num_gpu
    elif cfg:
        options["num_gpu"] = cfg.num_gpu
    if req.num_thread is not None:
        options["num_thread"] = req.num_thread
    elif cfg and cfg.num_thread:
        options["num_thread"] = cfg.num_thread
    if req.reasoning_effort:
        options["reasoning_effort"] = req.reasoning_effort

    payload: dict = {
        "model": req.model,
        "messages": messages,
        "stream": True,
        "options": options,
    }
    if req.think is not None:
        payload["think"] = req.think
    return payload


# ---------------------------------------------------------------------------
# Conversation CRUD
# ---------------------------------------------------------------------------
@router.get("/conversations", response_model=list[ConversationOut], summary="会话列表")
def list_conversations(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the current user's conversations, most recently active first."""
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


@router.post("/conversations", response_model=ConversationOut, summary="新建会话")
def create_conversation(
    payload: ConversationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new conversation (title optional, defaulted to 新对话)."""
    conv = Conversation(user_id=user.id, title=(payload.title or "").strip() or "新对话")
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/conversations/{cid}", response_model=ConversationDetail, summary="会话详情")
def get_conversation(
    cid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return a conversation with all its messages."""
    return _get_owned_conversation(db, cid, user)


@router.patch("/conversations/{cid}", response_model=ConversationOut, summary="重命名会话")
def rename_conversation(
    cid: int,
    payload: ConversationRename,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename a conversation."""
    conv = _get_owned_conversation(db, cid, user)
    conv.title = payload.title.strip() or conv.title
    db.commit()
    db.refresh(conv)
    return conv


@router.delete("/conversations/{cid}", status_code=status.HTTP_204_NO_CONTENT, summary="删除会话")
def delete_conversation(
    cid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a conversation and all its messages."""
    conv = _get_owned_conversation(db, cid, user)
    db.delete(conv)
    db.commit()


# ---------------------------------------------------------------------------
# Streaming chat
# ---------------------------------------------------------------------------
@router.post("/chat", summary="流式聊天")
async def chat(payload: ChatRequest, user: User = Depends(get_current_user)):
    """Stream a chat completion through Ollama and persist both messages.

    The full history is replayed to Ollama each time (stored in SQLite),
    so the client only sends the new user message plus parameters.
    """
    # Validate the conversation up-front (before opening the stream)
    if not payload.regenerate and not payload.content.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="消息内容不能为空")
    pre = SessionLocal()
    try:
        conv = pre.get(Conversation, payload.conversation_id)
        if conv is None or conv.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="会话不存在")
        conv_id = conv.id
    finally:
        pre.close()

    async def event_stream():
        db = SessionLocal()
        try:
            # 1. Persist the user message (skipped when regenerating)
            if payload.regenerate:
                # 删除最后一条 assistant 回复，用现有历史重新生成
                last = (
                    db.query(Message)
                    .filter(
                        Message.conversation_id == conv_id,
                        Message.role == "assistant",
                    )
                    .order_by(Message.id.desc())
                    .first()
                )
                if last is not None:
                    db.delete(last)
                    db.commit()
            else:
                db.add(
                    Message(
                        conversation_id=conv_id,
                        role="user",
                        content=payload.content,
                        model=payload.model,
                    )
                )
                # Auto-title the conversation from the first user message
                conv = db.get(Conversation, conv_id)
                if conv is not None and conv.title in ("新对话", ""):
                    conv.title = payload.content.strip()[:20] or conv.title
                db.commit()

            # 2. Load full history (including the message just saved)
            history = (
                db.query(Message)
                .filter(Message.conversation_id == conv_id)
                .order_by(Message.id.asc())
                .all()
            )

            # 3. Saved per-model defaults
            cfg = (
                db.query(ModelConfig)
                .filter(ModelConfig.model_name == payload.model)
                .first()
            )

            # 3b. RAG: retrieve context from selected knowledge bases
            rag_context = ""
            if payload.knowledge_ids:
                try:
                    query_vec = await ollama.embeddings(
                        settings.embed_model, payload.content
                    )
                    results = retrieve_chunks(
                        db,
                        np.asarray(query_vec, dtype=np.float32),
                        document_ids=payload.knowledge_ids,
                        top_k=4,
                    )
                    rag_context = "\n\n".join(r["content"] for r in results)
                except (httpx.HTTPError, RuntimeError) as exc:
                    logger.warning("知识库检索失败: %s", exc)
                    yield _sse(
                        {
                            "type": "notice",
                            "message": "知识库检索失败（请确认 Ollama 已安装嵌入模型）",
                        }
                    )

            ollama_payload = _build_ollama_payload(payload, history, cfg, rag_context)

            # 4. Stream from Ollama, forward deltas, persist the assistant reply
            assistant_parts: list[str] = []
            try:
                async for chunk in ollama.chat_stream(ollama_payload):
                    piece = (chunk.get("message") or {}).get("content") or ""
                    if piece:
                        assistant_parts.append(piece)
                        yield _sse({"type": "delta", "content": piece})
                    if chunk.get("done"):
                        full = "".join(assistant_parts)
                        db.add(
                            Message(
                                conversation_id=conv_id,
                                role="assistant",
                                content=full,
                                model=payload.model,
                            )
                        )
                        conv = db.get(Conversation, conv_id)
                        if conv is not None:
                            conv.updated_at = utcnow()
                        db.commit()
                        yield _sse(
                            {
                                "type": "done",
                                "content": full,
                                "conversation_id": conv_id,
                                "model": payload.model,
                            }
                        )
                        break
            except httpx.HTTPStatusError as exc:
                logger.warning("模型后端返回错误: %s", exc.response.status_code)
                yield _sse(
                    {
                        "type": "error",
                        "message": f"模型后端错误（{ollama.http_error_detail(exc)}）。请确认模型服务已启动并成功加载所选模型。",
                    }
                )
            except httpx.HTTPError as exc:
                logger.warning("模型后端连接失败: %s", exc)
                yield _sse(
                    {
                        "type": "error",
                        "message": f"无法连接模型后端 {settings.ollama_base_url}（{ollama.http_error_detail(exc)}），请确认服务已启动",
                    }
                )
        finally:
            db.close()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
