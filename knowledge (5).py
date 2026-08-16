"""Knowledge base helpers: text extraction, chunking, embeddings, retrieval."""

import io
import logging
import re

import numpy as np
from sqlalchemy.orm import Session

from ..models import DocumentChunk

logger = logging.getLogger("olmwed.knowledge")


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
def extract_text(filename: str, data: bytes) -> str:
    """Extract plain text from an uploaded file (txt / md / pdf)."""
    suffix = (filename or "").lower().rsplit(".", 1)[-1]

    if suffix == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            pages = []
            for page in reader.pages:
                try:
                    pages.append(page.extract_text() or "")
                except Exception:  # noqa: BLE001 — one bad page must not kill the doc
                    continue
            return "\n".join(pages)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF 解析失败: %s", exc)
            return ""

    # txt / md / others: try common encodings
    for enc in ("utf-8", "gb18030", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_text(text: str, size: int = 600, overlap: int = 80) -> list[str]:
    """Split text into overlapping chunks by paragraph boundaries.

    ``size``/``overlap`` are in characters (suitable for Chinese and English).
    """
    text = re.sub(r"\n{3,}", "\n\n", text or "").strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if not para:
            continue
        if len(current) + len(para) + 2 <= size:
            current = f"{current}\n\n{para}" if current else para
            continue
        if current:
            chunks.append(current)
            current = ""
        # Very long paragraph -> hard split with overlap
        while len(para) > size:
            chunks.append(para[:size])
            para = para[size - overlap :]
        current = para

    if current:
        chunks.append(current)
    return chunks


# ---------------------------------------------------------------------------
# Embeddings / similarity
# ---------------------------------------------------------------------------
def serialize_embedding(vector: list[float]) -> bytes:
    """float32 bytes for SQLite BLOB storage."""
    return np.asarray(vector, dtype=np.float32).tobytes()


def deserialize_embedding(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def retrieve_chunks(
    db: Session,
    query_embedding: np.ndarray,
    document_ids: list[int] | None = None,
    top_k: int = 4,
    max_candidates: int = 500,
) -> list[dict]:
    """Brute-force cosine search over stored chunks (fine for local scale)."""
    q = db.query(DocumentChunk)
    if document_ids:
        q = q.filter(DocumentChunk.document_id.in_(document_ids))

    scored: list[tuple[float, DocumentChunk]] = []
    for chunk in q.limit(max_candidates).all():
        vec = deserialize_embedding(chunk.embedding)
        scored.append((cosine_similarity(query_embedding, vec), chunk))

    scored.sort(key=lambda x: -x[0])
    return [
        {
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "content": c.content,
            "score": round(s, 4),
        }
        for s, c in scored[:top_k]
    ]
