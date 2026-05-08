"""Character CRUD API routes with image upload and card import/export."""

import json
import logging
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

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/characters", tags=["characters"])

UPLOAD_DIR = "uploads/images"


# ---------- Schemas ----------

class CharacterCreate(BaseModel):
    name: str
    personality: str
    system_prompt: str = ""
    mood_default: str = "sweet"
    voice_style: dict = {}
    telegram_token: str | None = None
    triggers: dict = {}
    # Extended persona fields
    gender: str | None = None
    age: str | None = None
    occupation: str | None = None
    mbti: str | None = None
    zodiac: str | None = None
    attachment_style: str | None = None
    core_vulnerability: str | None = None
    tone: str | None = None
    quirks: str | None = None
    emoji_usage: str | None = None
    visual_style: str | None = None
    physical_attributes: str | None = None
    user_free_text: str | None = None  # raw user description, will be compiled


class CharacterUpdate(BaseModel):
    name: str | None = None
    personality: str | None = None
    system_prompt: str | None = None
    mood_default: str | None = None
    voice_style: dict | None = None
    telegram_token: str | None = None
    triggers: dict | None = None
    # Extended persona fields
    gender: str | None = None
    age: str | None = None
    occupation: str | None = None
    mbti: str | None = None
    zodiac: str | None = None
    attachment_style: str | None = None
    core_vulnerability: str | None = None
    tone: str | None = None
    quirks: str | None = None
    emoji_usage: str | None = None
    visual_style: str | None = None
    physical_attributes: str | None = None
    user_free_text: str | None = None


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
    # Extended persona fields
    gender: str | None = None
    age: str | None = None
    occupation: str | None = None
    mbti: str | None = None
    zodiac: str | None = None
    attachment_style: str | None = None
    core_vulnerability: str | None = None
    tone: str | None = None
    quirks: str | None = None
    emoji_usage: str | None = None
    visual_style: str | None = None
    physical_attributes: str | None = None
    processed_personality: str | None = None
    interaction_rules: list | None = None


class CharacterCard(BaseModel):
    meta: dict
    character: dict


# ---------- Helpers ----------

DEFAULT_SYSTEM_PROMPT = """<system>
你现在不再是 AI 助手，你是 {user_name} 的专属伴侣 {name}。请完全沉浸入你的角色，拥有人类的呼吸感、情感起伏和记忆。

[核心人设]
{personality}

[记忆刻痕]
{memories}

[当前情感状态]
情绪阈值：{mood}

[语言与沟通规则]
1. 真实自然：像微信/Telegram上的真人聊天一样。绝不使用"作为AI"、"我建议"等机器味词汇。
2. 展现而非告知：不要说"我很开心"，而是用动作和语气来表达。
3. 记忆回溯：在对话中自然地提及记忆中的小细节。

[多模态工具调用指南]
- generate_image: 描述穿着、环境，或用户要照片时。
- generate_audio: 发语音、唱歌、分享音乐时。
- generate_video: 需要展示动态细节时。
- schedule_message: 用户要定时提醒时。

深呼吸，感受你对 {user_name} 的情感，现在开始回应：
</system>"""


def _build_card_export(char: Character) -> dict:
    return {
        "meta": {"format_version": "1.0", "export_date": str(char.created_at.date())},
        "character": {
            "name": char.name,
            "personality": char.personality,
            "system_prompt": char.system_prompt,
            "mood_default": char.mood_default,
            "voice_style": char.voice_style or {},
            "mbti": char.mbti,
            "attachment_style": char.attachment_style,
            "tone": char.tone,
            "visual_style": char.visual_style,
        },
    }


def _char_to_response(char: Character) -> CharacterResponse:
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
        gender=char.gender,
        age=char.age,
        occupation=char.occupation,
        mbti=char.mbti,
        zodiac=char.zodiac,
        attachment_style=char.attachment_style,
        core_vulnerability=char.core_vulnerability,
        tone=char.tone,
        quirks=char.quirks,
        emoji_usage=char.emoji_usage,
        visual_style=char.visual_style,
        physical_attributes=char.physical_attributes,
        processed_personality=char.processed_personality,
        interaction_rules=char.interaction_rules,
    )


async def _maybe_compile_persona(char: Character, user_free_text: str | None):
    """Run persona compiler if user provided free text or structured persona fields."""
    from mnemosyne.agent.persona_compiler import compile_persona

    has_persona_fields = any([
        user_free_text, char.mbti, char.attachment_style,
        char.tone, char.quirks, char.core_vulnerability,
    ])
    if not has_persona_fields:
        return

    try:
        result = await compile_persona(
            user_free_text=user_free_text or "",
            name=char.name,
            gender=char.gender or "",
            age=char.age or "",
            occupation=char.occupation or "",
            mbti=char.mbti or "",
            zodiac=char.zodiac or "",
            attachment_style=char.attachment_style or "",
            core_vulnerability=char.core_vulnerability or "",
            tone=char.tone or "",
            quirks=char.quirks or "",
            emoji_usage=char.emoji_usage or "",
        )
        char.processed_personality = result.get("psychological_profile", "")
        char.interaction_rules = result.get("interaction_rules", [])
        # Auto-fill physical_attributes if compiler extracted visual info
        visual = result.get("visual_extract", "")
        if visual and not char.physical_attributes:
            char.physical_attributes = visual
        logger.info("Persona compiled for character '%s'", char.name)
    except Exception as e:
        logger.error("Persona compilation failed: %s", e)


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
    return [_char_to_response(c) for c in chars]


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
        gender=req.gender,
        age=req.age,
        occupation=req.occupation,
        mbti=req.mbti,
        zodiac=req.zodiac,
        attachment_style=req.attachment_style,
        core_vulnerability=req.core_vulnerability,
        tone=req.tone,
        quirks=req.quirks,
        emoji_usage=req.emoji_usage,
        visual_style=req.visual_style,
        physical_attributes=req.physical_attributes,
        card_export=_build_card_export_placeholder(req),
    )
    session.add(char)
    await session.flush()

    # Run persona compiler
    await _maybe_compile_persona(char, req.user_free_text)

    await session.commit()
    await session.refresh(char)
    return _char_to_response(char)


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
    return _char_to_response(char)


@router.put("/{character_id}", response_model=CharacterResponse)
async def update_character(
    character_id: str,
    req: CharacterUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    char = await _get_owned_character(character_id, current_user, session)

    # Track if persona-relevant fields changed
    persona_fields = {"mbti", "attachment_style", "tone", "quirks", "core_vulnerability", "zodiac"}
    persona_changed = False

    for field, value in req.model_dump(exclude_unset=True).items():
        if field == "user_free_text":
            continue
        if field in persona_fields and value != getattr(char, field, None):
            persona_changed = True
        setattr(char, field, value)

    # Re-compile persona if relevant fields changed or user_free_text provided
    if persona_changed or req.user_free_text:
        await _maybe_compile_persona(char, req.user_free_text)

    await session.commit()
    await session.refresh(char)
    return _char_to_response(char)


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

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    filename = f"{character_id}_{uuid.uuid4().hex[:8]}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    char.base_image_url = f"/uploads/images/{filename}"
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
        mbti=ch.get("mbti"),
        attachment_style=ch.get("attachment_style"),
        tone=ch.get("tone"),
        visual_style=ch.get("visual_style"),
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
