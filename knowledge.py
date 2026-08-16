"""Knowledge base (RAG): document upload, text extraction, embedding, search.

Embedding is done with an Ollama embedding model (default nomic-embed-text).
Chunks + float32 embeddings are stored in SQLite (document_chunks table);
retrieval is a brute-force cosine search — plenty for local-scale corpora.
"""

import logging
import time
from datetime import datetime
from pathlib import Path

import httpx
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import Document, DocumentChunk, User
from ..services import knowledge as kb
from ..services import ollama

logger = logging.getLogger("olmwed.knowledge")
router = APIRouter()

ALLOWED_EXT = {".txt", ".md", ".pdf"}
KNOWLEDGE_DIR = Path("data/knowledge")


class DocumentOut(BaseModel):
    id: int
    name: str
    chunk_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    document_ids: list[int] = []
    top_k: int = Field(default=5, ge=1, le=20)


# ---------------------------------------------------------------------------
# Upload & indexing
# ---------------------------------------------------------------------------
@router.post("/upload", summary="上传文档并建立索引")
async def upload_document(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accept txt / md / pdf, extract text, chunk it, and embed via Ollama."""
    filename = Path(file.filename or "doc.txt").name
    suffix = filename.lower().rsplit(".", 1)[-1]
    if f".{suffix}" not in ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="仅支持 txt / md / pdf 文件")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="文件为空")

    text = kb.extract_text(filename, data).strip()
    if not text:
        raise HTTPException(status_code=400, detail="无法从文件中提取文本（PDF 可能是扫描件）")

    # Keep the original file on disk (data/knowledge/)
    KNOWLEDGE_DIR.mkdir(parents=True, exist_ok=True)
    file_path = KNOWLEDGE_DIR / f"{int(time.time())}_{filename}"
    file_path.write_bytes(data)

    doc = Document(name=filename, content=text, file_path=str(file_path))
    db.add(doc)
    db.flush()

    chunks = kb.chunk_text(text)
    embed_model = settings.embed_model
    try:
        for i, chunk in enumerate(chunks):
            vector = await ollama.embeddings(embed_model, chunk)
            db.add(
                DocumentChunk(
                    document_id=doc.id,
                    chunk_index=i,
                    content=chunk,
                    embedding=kb.serialize_embedding(vector),
                )
            )
    except httpx.HTTPError as exc:
        db.rollback()
        logger.warning("向量化失败: %s", exc)
        raise HTTPException(
            status_code=502,
            detail=f"向量化失败：请确认 Ollama 已安装嵌入模型 {embed_model}（运行 `ollama pull {embed_model}`）",
        )
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"向量化失败：{exc}")

    db.commit()
    logger.info("文档已索引: %s (%d 块)", filename, len(chunks))
    return {"id": doc.id, "name": doc.name, "chunks": len(chunks)}


@router.get("/documents", response_model=list[DocumentOut], summary="文档列表")
def list_documents(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List knowledge documents with their chunk counts."""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    counts = dict(
        db.query(DocumentChunk.document_id, func.count(DocumentChunk.id))
        .group_by(DocumentChunk.document_id)
        .all()
    )
    result = []
    for d in docs:
        out = DocumentOut.model_validate(d)
        out.chunk_count = counts.get(d.id, 0)
        result.append(out)
    return result


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除文档")
def delete_document(
    doc_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a document, its chunks and the stored file."""
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="文档不存在")
    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except OSError:
        logger.warning("无法删除文件 %s", doc.file_path)
    db.delete(doc)
    db.commit()


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------
@router.post("/search", summary="向量检索")
async def search(
    payload: SearchRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Embed the query and return the most similar chunks (cosine)."""
    try:
        vector = await ollama.embeddings(settings.embed_model, payload.query)
    except RuntimeError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"检索失败：请确认 Ollama 已安装嵌入模型 {settings.embed_model}",
        ) from exc

    query_emb = np.asarray(vector, dtype=np.float32)
    results = kb.retrieve_chunks(
        db, query_emb, document_ids=payload.document_ids or None, top_k=payload.top_k
    )
    return {"results": results}
