"""Post-conversation memory extraction using LLM."""

import json

import litellm
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from mnemosyne.agent.prompts import MEMORY_EXTRACTION_PROMPT
from mnemosyne.config import settings
from mnemosyne.db.models import Character, Conversation, Memory
from mnemosyne.memory.models import ExtractionResult, get_embedding


async def extract_memories(
    session: AsyncSession,
    character_id: str,
    conversation_limit: int = 10,
) -> ExtractionResult:
    """Extract key memories from recent conversation.

    Called asynchronously after each conversation ends.
    """
    # Get recent conversation
    result = await session.execute(
        select(Conversation)
        .where(Conversation.character_id == character_id)
        .order_by(Conversation.created_at.desc())
        .limit(conversation_limit)
    )
    messages = list(reversed(result.scalars().all()))
    if not messages:
        return ExtractionResult()

    # Format conversation for extraction
    conv_text = "\n".join(f"[{m.role}] {m.content}" for m in messages)

    # Call LLM for extraction
    try:
        response = await litellm.acompletion(
            model=f"{settings.llm_provider}/{settings.llm_model}" if settings.llm_provider != "openai" else settings.llm_model,
            messages=[
                {"role": "user", "content": MEMORY_EXTRACTION_PROMPT.format(conversation=conv_text)}
            ],
            api_key=settings.llm_api_key,
            api_base=settings.llm_base_url or None,
            max_tokens=512,
            temperature=0.3,
        )
        raw = response.choices[0].message.content or ""
        # Extract JSON from response
        json_match = raw.strip()
        if json_match.startswith("```"):
            json_match = json_match.split("```")[1]
            if json_match.startswith("json"):
                json_match = json_match[4:]
        extracted = json.loads(json_match)
    except (json.JSONDecodeError, Exception):
        return ExtractionResult()

    extraction = ExtractionResult(
        facts=extracted.get("facts", []),
        feelings=extracted.get("feelings", []),
        events=extracted.get("events", []),
    )

    # Store memories
    for fact in extraction.facts:
        await _store_memory(session, character_id, "fact", fact)

    for feeling in extraction.feelings:
        await _store_memory(session, character_id, "feeling", feeling, importance=0.7)

    for event in extraction.events:
        await _store_memory(session, character_id, "event", event, importance=0.8)

    await session.commit()
    return extraction


async def _store_memory(
    session: AsyncSession,
    character_id: str,
    memory_type: str,
    content: str,
    importance: float = 0.5,
    metadata: dict | None = None,
):
    """Store a single memory with embedding."""
    # Generate embedding
    try:
        embedding = await get_embedding(content)
    except Exception:
        embedding = None

    memory = Memory(
        character_id=character_id,
        type=memory_type,
        content=content,
        embedding=embedding,
        metadata_=metadata or {},
        importance=importance,
    )
    session.add(memory)


async def cleanup_old_conversations(session: AsyncSession, character_id: str, keep: int = 30):
    """Sliding window: keep only the most recent N conversation rounds."""
    # Count total messages
    count_result = await session.execute(
        select(func.count()).where(Conversation.character_id == character_id)
    )
    total = count_result.scalar()

    if total <= keep * 2:
        return

    # Delete oldest messages beyond the window
    from sqlalchemy import delete
    subq = (
        select(Conversation.id)
        .where(Conversation.character_id == character_id)
        .order_by(Conversation.created_at.asc())
        .limit(total - keep * 2)
    )
    await session.execute(delete(Conversation).where(Conversation.id.in_(subq)))
    await session.commit()
