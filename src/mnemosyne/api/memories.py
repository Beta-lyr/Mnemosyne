"""Memory management API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from mnemosyne.api.auth import get_current_user
from mnemosyne.db.models import Character, Memory, User
from mnemosyne.db.session import get_session

router = APIRouter(prefix="/api/memories", tags=["memories"])


class MemoryResponse(BaseModel):
    id: str
    character_id: str
    type: str
    content: str
    metadata: dict
    importance: float
    created_at: str


@router.get("/{character_id}", response_model=list[MemoryResponse])
async def list_memories(
    character_id: str,
    type: str | None = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _verify_character_access(character_id, current_user, session)
    query = select(Memory).where(Memory.character_id == character_id)
    if type:
        query = query.where(Memory.type == type)
    query = query.order_by(Memory.created_at.desc()).limit(limit)

    result = await session.execute(query)
    memories = result.scalars().all()
    return [
        MemoryResponse(
            id=str(m.id),
            character_id=str(m.character_id),
            type=m.type,
            content=m.content,
            metadata=m.metadata_ or {},
            importance=m.importance,
            created_at=m.created_at.isoformat(),
        )
        for m in memories
    ]


@router.delete("/{memory_id}")
async def delete_memory(
    memory_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Memory).where(Memory.id == memory_id))
    memory = result.scalar_one_or_none()
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    await session.delete(memory)
    await session.commit()
    return {"ok": True}


@router.delete("/{character_id}/all")
async def clear_all_memories(
    character_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _verify_character_access(character_id, current_user, session)
    await session.execute(delete(Memory).where(Memory.character_id == character_id))
    await session.commit()
    return {"ok": True, "message": "All memories cleared"}


@router.get("/{character_id}/export")
async def export_memories(
    character_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _verify_character_access(character_id, current_user, session)
    result = await session.execute(
        select(Memory).where(Memory.character_id == character_id).order_by(Memory.created_at)
    )
    memories = result.scalars().all()
    return [
        {
            "type": m.type,
            "content": m.content,
            "metadata": m.metadata_ or {},
            "importance": m.importance,
            "created_at": m.created_at.isoformat(),
        }
        for m in memories
    ]


async def _verify_character_access(character_id: str, user: User, session: AsyncSession):
    result = await session.execute(
        select(Character).where(Character.id == character_id, Character.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Character not found")
