"""Character CRUD API routes with image upload and card import/export."""

import json
import os
import uuid

import yaml
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from mnemosyne.api.auth import get_current_user
from mnemosyne.db.models import Character, User
from mnemosyne.db.session import get_session

router = APIRouter(prefix="/api/characters", tags=["characters"])

UPLOAD_DIR = "uploads"


# ---------- Schemas ----------

class CharacterCreate(BaseModel):
    name: str
    personality: str
    system_prompt: str = ""
    mood_default: str = "sweet"
    voice_style: dict = {}
    telegram_token: str | None = None
    triggers: dict = {}


class CharacterUpdate(BaseModel):
    name: str | None = None
    personality: str | None = None
    system_prompt: str | None = None
    mood_default: str | None = None
    voice_style: dict | None = None
    telegram_token: str | None = None
    triggers: dict | None = None


class CharacterResponse(BaseModel):
    id: str
    name: str
    personality: str
    system_prompt: str
    base_image_url: str | None
    mood_default: str
    voice_style: dict
    telegram_token: str | None
    created_at: str


class CharacterCard(BaseModel):
    meta: dict
    character: dict


# ---------- Helpers ----------

DEFAULT_SYSTEM_PROMPT = """你是{user_name}的虚拟伴侣{name}。

你的性格设定：
{personality}

你记得关于{user_name}的事情：
{memories}

你当前的心情：{mood}

请用符合你性格的方式回复。保持角色一致性，不要跳出角色。
如果需要发照片，请调用生图工具。"""


def _build_card_export(char: Character) -> dict:
    return {
        "meta": {"format_version": "1.0", "export_date": str(char.created_at.date())},
        "character": {
            "name": char.name,
            "personality": char.personality,
            "system_prompt": char.system_prompt,
            "mood_default": char.mood_default,
            "voice_style": char.voice_style or {},
        },
    }


# ---------- Routes ----------

@router.get("/", response_model=list[CharacterResponse])
async def list_characters(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Character).where(Character.user_id == current_user.id).order_by(Character.created_at)
    )
    chars = result.scalars().all()
    return [
        CharacterResponse(
            id=str(c.id),
            name=c.name,
            personality=c.personality,
            system_prompt=c.system_prompt,
            base_image_url=c.base_image_url,
            mood_default=c.mood_default,
            voice_style=c.voice_style or {},
            telegram_token=c.telegram_token,
            created_at=c.created_at.isoformat(),
        )
        for c in chars
    ]


@router.post("/", response_model=CharacterResponse)
async def create_character(
    req: CharacterCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    system_prompt = req.system_prompt or DEFAULT_SYSTEM_PROMPT.format(
        user_name="{user_name}", name=req.name, personality=req.personality, memories="{memories}", mood="{mood}"
    )
    char = Character(
        user_id=current_user.id,
        name=req.name,
        personality=req.personality,
        system_prompt=system_prompt,
        mood_default=req.mood_default,
        voice_style=req.voice_style,
        telegram_token=req.telegram_token,
        card_export=_build_card_export_placeholder(req),
    )
    session.add(char)
    await session.commit()
    await session.refresh(char)
    return CharacterResponse(
        id=str(char.id),
        name=char.name,
        personality=char.personality,
        system_prompt=char.system_prompt,
        base_image_url=char.base_image_url,
        mood_default=char.mood_default,
        voice_style=char.voice_style or {},
        telegram_token=char.telegram_token,
        created_at=char.created_at.isoformat(),
    )


def _build_card_export_placeholder(req: CharacterCreate) -> dict:
    return {
        "meta": {"format_version": "1.0"},
        "character": {
            "name": req.name,
            "personality": req.personality,
            "system_prompt": req.system_prompt or "",
            "mood_default": req.mood_default,
            "voice_style": req.voice_style,
        },
    }


@router.get("/{character_id}", response_model=CharacterResponse)
async def get_character(
    character_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    char = await _get_owned_character(character_id, current_user, session)
    return CharacterResponse(
        id=str(char.id),
        name=char.name,
        personality=char.personality,
        system_prompt=char.system_prompt,
        base_image_url=char.base_image_url,
        mood_default=char.mood_default,
        voice_style=char.voice_style or {},
        telegram_token=char.telegram_token,
        created_at=char.created_at.isoformat(),
    )


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    req: CharacterUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    char = await _get_owned_character(character_id, current_user, session)
    for field, value in req.model_dump(exclude_unset=True).items():
        setattr(char, field, value)
    await session.commit()
    await session.refresh(char)
    return CharacterResponse(
        id=str(char.id),
        name=char.name,
        personality=char.personality,
        system_prompt=char.system_prompt,
        base_image_url=char.base_image_url,
        mood_default=char.mood_default,
        voice_style=char.voice_style or {},
        telegram_token=char.telegram_token,
        created_at=char.created_at.isoformat(),
    )


@router.delete("/{character_id}")
async def delete_character(
    character_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    char = await _get_owned_character(character_id, current_user, session)
    await session.delete(char)
    await session.commit()
    return {"ok": True}


@router.post("/{character_id}/image")
async def upload_base_image(
    character_id: str,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    char = await _get_owned_character(character_id, current_user, session)

    ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    filename = f"{character_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    char.base_image_url = f"/uploads/{filename}"
    await session.commit()
    return {"url": char.base_image_url}


@router.get("/{character_id}/export")
async def export_character_card(
    character_id: str,
    format: str = "yaml",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    char = await _get_owned_character(character_id, current_user, session)
    card = _build_card_export(char)

    if format == "json":
        return card
    return yaml.dump(card, allow_unicode=True, default_flow_style=False)


@router.post("/import")
async def import_character_card(
    card: CharacterCard,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    ch = card.character
    system_prompt = ch.get("system_prompt", "")
    if not system_prompt:
        system_prompt = DEFAULT_SYSTEM_PROMPT.format(
            user_name="{user_name}", name=ch["name"],
            personality=ch["personality"], memories="{memories}", mood="{mood}"
        )

    char = Character(
        user_id=current_user.id,
        name=ch["name"],
        personality=ch["personality"],
        system_prompt=system_prompt,
        mood_default=ch.get("mood_default", "sweet"),
        voice_style=ch.get("voice_style", {}),
    )
    session.add(char)
    await session.commit()
    await session.refresh(char)
    return {"id": str(char.id), "name": char.name}


async def _get_owned_character(
    character_id: str, user: User, session: AsyncSession
) -> Character:
    result = await session.execute(
        select(Character).where(Character.id == character_id, Character.user_id == user.id)
    )
    char = result.scalar_one_or_none()
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char
