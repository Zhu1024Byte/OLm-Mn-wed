"""API Key management (for the OpenAI-compatible API on port 3001)."""

import secrets
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import ApiKey, User

router = APIRouter()


class KeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class KeyRename(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class ApiKeyOut(BaseModel):
    id: int
    name: str
    key: str
    created_at: datetime
    last_used: datetime | None
    enabled: bool

    model_config = {"from_attributes": True}


def _generate_key() -> str:
    """Generate a scoped API key: sk-olmwed-<random>."""
    return f"sk-olmwed-{secrets.token_urlsafe(32)}"


def _get_owned_key(db: Session, kid: int, user: User) -> ApiKey:
    row = db.get(ApiKey, kid)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="API Key 不存在")
    return row


@router.get("/keys", response_model=list[ApiKeyOut], summary="API Key 列表")
def list_keys(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List the current user's API keys, newest first."""
    return (
        db.query(ApiKey)
        .filter(ApiKey.user_id == user.id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )


@router.post("/keys", response_model=ApiKeyOut, summary="创建 API Key")
def create_key(
    payload: KeyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a new API key. The plaintext key is returned only once."""
    row = ApiKey(user_id=user.id, name=payload.name.strip(), key=_generate_key())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/keys/{kid}", response_model=ApiKeyOut, summary="重命名 API Key")
def rename_key(
    kid: int,
    payload: KeyRename,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Rename an API key."""
    row = _get_owned_key(db, kid, user)
    row.name = payload.name.strip() or row.name
    db.commit()
    db.refresh(row)
    return row


@router.delete("/keys/{kid}", status_code=status.HTTP_204_NO_CONTENT, summary="删除 API Key")
def delete_key(
    kid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete an API key; it stops working immediately."""
    row = _get_owned_key(db, kid, user)
    db.delete(row)
    db.commit()
