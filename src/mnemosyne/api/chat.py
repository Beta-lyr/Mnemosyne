"""Chat API routes: REST + WebSocket for real-time conversation."""

import asyncio
import json
from datetime import datetime

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemosyne.agent.core import DialogEngine
from mnemosyne.api.auth import get_current_user
from mnemosyne.db.models import Character, Conversation, User
from mnemosyne.db.session import get_session
from mnemosyne.emotion.state import EmotionManager

router = APIRouter(prefix="/api/chat", tags=["chat"])

dialog_engine = DialogEngine()
emotion_manager = EmotionManager()


class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: str | None = None
    role: str
    content: str
    image_url: str | None = None
    audio_url: str | None = None
    video_url: str | None = None
    media_status: str | None = None
    created_at: str | None = None


class HistoryResponse(BaseModel):
    messages: list[MessageResponse]
    has_more: bool


class DeleteMediaRequest(BaseModel):
    ids: list[str] | None = None
    clear_all: bool = False
    media_type: str = "all"  # "all" | "image" | "audio" | "video"


@router.get("/{character_id}/history", response_model=HistoryResponse)
async def get_chat_history(
    character_id: str,
    limit: int = 30,
    before: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _verify_character_access(character_id, current_user, session)
    query = (
        select(Conversation)
        .where(Conversation.character_id == character_id)
    )
    if before:
        query = query.where(Conversation.created_at < datetime.fromisoformat(before))
    query = query.order_by(Conversation.created_at.desc()).limit(limit + 1)
    result = await session.execute(query)
    rows = list(result.scalars().all())
    has_more = len(rows) > limit
    messages = list(reversed(rows[:limit]))
    return HistoryResponse(
        messages=[
            MessageResponse(
                id=str(m.id),
                role=m.role,
                content=m.content,
                image_url=m.image_url,
                audio_url=m.audio_url,
                video_url=m.video_url,
                media_status=getattr(m, 'media_status', None),
                created_at=m.created_at.isoformat() if m.created_at else None,
            )
            for m in messages
        ],
        has_more=has_more,
    )


@router.post("/{character_id}/message", response_model=MessageResponse)
async def send_message_rest(
    character_id: str,
    req: MessageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _verify_character_access(character_id, current_user, session)

    # Save user message
    user_msg = Conversation(character_id=character_id, role="user", content=req.content)
    session.add(user_msg)
    await session.commit()

    # Mood-based delay
    result = await session.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    delay = await emotion_manager.get_reply_delay(character_id, character.mood_default if character else "sweet")
    await asyncio.sleep(delay)

    # Check read-not-reply
    should_silence = await emotion_manager.should_silence(character_id, character.mood_default if character else "sweet")
    if should_silence:
        return MessageResponse(
            role="assistant",
            content="",
            media_status="read_only",
        )

    # Generate response (text only, media async)
    response_text, pending_media = await dialog_engine.process_message(
        character_id=character_id,
        user_message=req.content,
        session=session,
    )

    # Save assistant response
    has_pending = bool(pending_media)
    assistant_msg = Conversation(
        character_id=character_id,
        role="assistant",
        content=response_text,
        has_image=False,
        media_status="pending" if has_pending else None,
    )
    session.add(assistant_msg)
    await session.commit()
    await session.refresh(assistant_msg)

    # Launch media generation in background
    if has_pending:
        asyncio.create_task(
            dialog_engine.generate_media_background(
                character_id=character_id,
                message_id=str(assistant_msg.id),
                pending_media=pending_media,
            )
        )

    return MessageResponse(
        id=str(assistant_msg.id),
        role="assistant",
        content=response_text,
        media_status="pending" if has_pending else None,
        created_at=assistant_msg.created_at.isoformat() if assistant_msg.created_at else None,
    )


@router.websocket("/{character_id}/ws")
async def chat_websocket(websocket: WebSocket, character_id: str):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    from mnemosyne.db.session import async_session

    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            content = message_data.get("content", "")

            async with async_session() as session:
                # Save user message
                user_msg = Conversation(character_id=character_id, role="user", content=content)
                session.add(user_msg)
                await session.commit()

                # Mood-based delay
                result = await session.execute(select(Character).where(Character.id == character_id))
                character = result.scalar_one_or_none()
                delay = await emotion_manager.get_reply_delay(character_id, character.mood_default if character else "sweet")
                await asyncio.sleep(delay)

                # Check read-not-reply
                should_silence = await emotion_manager.should_silence(character_id, character.mood_default if character else "sweet")
                if should_silence:
                    await websocket.send_text(json.dumps({"type": "read_receipt"}))
                    continue

                # Generate response (text only)
                response_text, pending_media = await dialog_engine.process_message(
                    character_id=character_id,
                    user_message=content,
                    session=session,
                )

                # Save assistant response
                has_pending = bool(pending_media)
                assistant_msg = Conversation(
                    character_id=character_id,
                    role="assistant",
                    content=response_text,
                    has_image=False,
                    media_status="pending" if has_pending else None,
                )
                session.add(assistant_msg)
                await session.commit()
                await session.refresh(assistant_msg)

            msg_id = str(assistant_msg.id)

            # Send text reply immediately
            await websocket.send_text(
                json.dumps({
                    "id": msg_id,
                    "role": "assistant",
                    "content": response_text,
                    "image_url": None,
                    "audio_url": None,
                    "video_url": None,
                    "media_status": "pending" if has_pending else None,
                    "created_at": assistant_msg.created_at.isoformat() if assistant_msg.created_at else None,
                })
            )

            # Launch media generation in background
            if has_pending:
                async def _on_media_complete(mid, img, aud, vid):
                    """Send media update back through WebSocket."""
                    try:
                        await websocket.send_text(
                            json.dumps({
                                "type": "media_update",
                                "message_id": mid,
                                "image_url": img,
                                "audio_url": aud,
                                "video_url": vid,
                            })
                        )
                    except Exception:
                        pass

                asyncio.create_task(
                    dialog_engine.generate_media_background(
                        character_id=character_id,
                        message_id=msg_id,
                        pending_media=pending_media,
                        on_complete=_on_media_complete,
                    )
                )

    except WebSocketDisconnect:
        pass


@router.get("/{character_id}/media")
async def list_media(
    character_id: str,
    media_type: str = "all",
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """List media files for a character's conversations."""
    await _verify_character_access(character_id, current_user, session)
    query = select(Conversation).where(
        Conversation.character_id == character_id,
        Conversation.role == "assistant",
    )
    result = await session.execute(query.order_by(Conversation.created_at.desc()))
    messages = result.scalars().all()

    media_items = []
    for m in messages:
        if media_type in ("all", "image") and m.image_url:
            media_items.append({"message_id": str(m.id), "type": "image", "url": m.image_url, "created_at": m.created_at.isoformat() if m.created_at else None})
        if media_type in ("all", "audio") and m.audio_url:
            media_items.append({"message_id": str(m.id), "type": "audio", "url": m.audio_url, "created_at": m.created_at.isoformat() if m.created_at else None})
        if media_type in ("all", "video") and m.video_url:
            media_items.append({"message_id": str(m.id), "type": "video", "url": m.video_url, "created_at": m.created_at.isoformat() if m.created_at else None})
    return media_items


@router.delete("/{character_id}/media")
async def delete_media(
    character_id: str,
    body: DeleteMediaRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete media files and clear URLs from conversation records."""
    await _verify_character_access(character_id, current_user, session)
    import os

    if body.clear_all:
        query = select(Conversation).where(
            Conversation.character_id == character_id,
            Conversation.role == "assistant",
        )
        result = await session.execute(query)
        messages = result.scalars().all()
        for m in messages:
            _clear_media_from_message(m, body.media_type)
        await session.commit()
    elif body.ids:
        for msg_id in body.ids:
            result = await session.execute(select(Conversation).where(Conversation.id == msg_id))
            m = result.scalar_one_or_none()
            if m:
                _clear_media_from_message(m, body.media_type)
        await session.commit()

    return {"ok": True}


def _clear_media_from_message(m: Conversation, media_type: str):
    """Clear media URLs from a conversation message."""
    if media_type in ("all", "image") and m.image_url:
        m.image_url = None
    if media_type in ("all", "audio") and m.audio_url:
        m.audio_url = None
    if media_type in ("all", "video") and m.video_url:
        m.video_url = None
    m.media_status = "cleared"


async def _verify_character_access(character_id: str, user: User, session: AsyncSession):
    result = await session.execute(
        select(Character).where(Character.id == character_id, Character.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Character not found")
