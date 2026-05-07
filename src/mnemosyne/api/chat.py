"""Chat API routes: REST + WebSocket for real-time conversation."""

import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from mnemosyne.agent.core import DialogEngine
from mnemosyne.api.auth import get_current_user
from mnemosyne.db.models import Character, Conversation, User
from mnemosyne.db.session import get_session

router = APIRouter(prefix="/api/chat", tags=["chat"])

dialog_engine = DialogEngine()


class MessageRequest(BaseModel):
    content: str


class MessageResponse(BaseModel):
    role: str
    content: str
    image_url: str | None = None


@router.get("/{character_id}/history", response_model=list[MessageResponse])
async def get_chat_history(
    character_id: str,
    limit: int = 60,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    await _verify_character_access(character_id, current_user, session)
    result = await session.execute(
        select(Conversation)
        .where(Conversation.character_id == character_id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    messages = list(reversed(result.scalars().all()))
    return [
        MessageResponse(
            role=m.role,
            content=m.content,
            image_url=m.image_url,
        )
        for m in messages
    ]


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

    # Generate response
    response_text, image_url = await dialog_engine.process_message(
        character_id=character_id,
        user_message=req.content,
        session=session,
    )

    # Save assistant response
    assistant_msg = Conversation(
        character_id=character_id,
        role="assistant",
        content=response_text,
        has_image=image_url is not None,
        image_url=image_url,
    )
    session.add(assistant_msg)
    await session.commit()

    return MessageResponse(role="assistant", content=response_text, image_url=image_url)


@router.websocket("/{character_id}/ws")
async def chat_websocket(websocket: WebSocket, character_id: str):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    # For WebSocket we use a new session per message
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

                # Generate response
                response_text, image_url = await dialog_engine.process_message(
                    character_id=character_id,
                    user_message=content,
                    session=session,
                )

                # Save assistant response
                assistant_msg = Conversation(
                    character_id=character_id,
                    role="assistant",
                    content=response_text,
                    has_image=image_url is not None,
                    image_url=image_url,
                )
                session.add(assistant_msg)
                await session.commit()

            await websocket.send_text(
                json.dumps({"role": "assistant", "content": response_text, "image_url": image_url})
            )

    except WebSocketDisconnect:
        pass


async def _verify_character_access(character_id: str, user: User, session: AsyncSession):
    result = await session.execute(
        select(Character).where(Character.id == character_id, Character.user_id == user.id)
    )
    if not result.scalar_one_or_none():
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Character not found")
