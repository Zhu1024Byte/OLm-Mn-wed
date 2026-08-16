"""Persona (saved system prompt) management."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..database import get_db
from ..models import Persona, User

router = APIRouter()


class PersonaIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    prompt: str = Field(default="", max_length=20000)


class PersonaOut(BaseModel):
    id: int
    name: str
    prompt: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


def _get_owned(db: Session, pid: int, user: User) -> Persona:
    row = db.get(Persona, pid)
    if row is None or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="人格不存在")
    return row


@router.get("/personas", response_model=list[PersonaOut], summary="人格列表")
def list_personas(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """List the current user's saved personas."""
    return (
        db.query(Persona)
        .filter(Persona.user_id == user.id)
        .order_by(Persona.updated_at.desc())
        .all()
    )


@router.post("/personas", response_model=PersonaOut, summary="新建人格")
def create_persona(
    payload: PersonaIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save a new persona (system prompt preset)."""
    row = Persona(user_id=user.id, name=payload.name.strip(), prompt=payload.prompt)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/personas/{pid}", response_model=PersonaOut, summary="更新人格")
def update_persona(
    pid: int,
    payload: PersonaIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a persona's name / prompt."""
    row = _get_owned(db, pid, user)
    row.name = payload.name.strip()
    row.prompt = payload.prompt
    db.commit()
    db.refresh(row)
    return row


@router.delete("/personas/{pid}", status_code=status.HTTP_204_NO_CONTENT, summary="删除人格")
def delete_persona(
    pid: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a persona."""
    row = _get_owned(db, pid, user)
    db.delete(row)
    db.commit()
